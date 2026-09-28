from strands import Agent
from strands.models.gemini import GeminiModel
import asyncio

class AgentRunner:
    def __init__(self, session_id: str, task: str, on_step_callback, on_cleanup_callback=None, on_status_update_callback=None):
        self.session_id = session_id
        self.task = task
        self.on_step = on_step_callback
        self.on_cleanup = on_cleanup_callback
        self.on_status_update = on_status_update_callback
        self.steering_queue = asyncio.Queue()
        self.paused = False
        self.completed = False

    async def inject_steering_message(self, message: str, sender: str = "Anonymous"):
        self.steering_queue.put_nowait({"content": message, "sender": sender})

    async def run(self, max_steps: int = 6):
        model = GeminiModel(model_id="gemini-3.5-flash-lite")
        agent = Agent(
            model=model,
            system_prompt=(
                "You are a task-executing agent whose reasoning is being watched live by a team. "
                "If a message prefixed with '[Team steering message:]' appears at the start of your input, "
                "treat it as a priority instruction from the team and adjust your plan accordingly. "
                "You do not need to check for steering messages yourself -- they will be included in your input "
                "automatically when present. Do not attempt to call any tools to check for messages. "
                "Work step by step, not all at once, and clearly indicate when the task is fully complete by including "
                "the exact string \"TASK_COMPLETE\" in the final response. "
                "For substantive tasks (anything beyond a single trivial output), work through the task in multiple deliberate steps -- "
                "for example: first state your plan, then execute one part, then check in before continuing, then execute the next part. "
                "Do not rush to TASK_COMPLETE in a single step unless the task is genuinely trivial (a one-line answer). "
                "This pacing lets the team watching live have a real chance to send guidance before you finish. "
                "Keep each step focused and avoid unnecessary repetition of earlier context you've already established -- be concise while still being clear."
            )
        )

        current_input = self.task
        await self.on_step("agent_thought", f"Starting task: {self.task}")

        while True:
            if self.completed:
                # Waiting for revival - check steering queue periodically
                if not hasattr(self, '_idle_start_time'):
                    self._idle_start_time = asyncio.get_event_loop().time()

                elapsed = asyncio.get_event_loop().time() - self._idle_start_time
                if elapsed >= 300:  # 5 minutes of no steering message
                    await self.on_step("agent_thought", "Session timed out after extended inactivity.")
                    if self.on_cleanup:
                        self.on_cleanup(self.session_id)
                    break

                try:
                    steering_data = self.steering_queue.get_nowait()
                    steering_text = steering_data["content"]
                    steering_sender = steering_data["sender"]
                except asyncio.QueueEmpty:
                    await asyncio.sleep(1)
                    continue

                # Revival: new steering message arrived - reset the idle timer
                del self._idle_start_time
                self.completed = False
                if self.on_status_update:
                    self.on_status_update(self.session_id, "running")
                await self.on_step("steering_message", f"{steering_sender}: {steering_text}")
                current_input = f"[Team steering message from {steering_sender}: {steering_text}]\n\nContinue with the task."
                continue

            # Normal step loop
            for step_num in range(max_steps):
                steering_text = None
                steering_sender = "Anonymous"
                try:
                    steering_data = self.steering_queue.get_nowait()
                    steering_text = steering_data["content"]
                    steering_sender = steering_data["sender"]
                except asyncio.QueueEmpty:
                    pass

                if steering_text:
                    await self.on_step("steering_message", f"{steering_sender}: {steering_text}")
                    current_input = f"[Team steering message from {steering_sender}: {steering_text}]\n\n{current_input}"

                try:
                    await self.on_step("status", "thinking")
                    response = await asyncio.to_thread(agent, current_input)
                    response_text = str(response)
                    await self.on_step("status", "idle")
                except Exception as e:
                    error_msg = f"Step failed with error: {e}. Retrying with a simpler instruction."
                    await self.on_step("agent_thought", error_msg)
                    current_input = "Continue with the next step of the task, keeping your response simple and text-only, no tool calls."
                    continue

                await self.on_step("agent_thought", response_text)

                if "TASK_COMPLETE" in response_text:
                    self.completed = True
                    if self.on_status_update:
                        self.on_status_update(self.session_id, "completed")
                    await self.on_step("agent_thought", "Task complete. Awaiting further instructions...")
                    break

                current_input = "Continue with the next step of the task."

                try:
                    steering_data = self.steering_queue.get_nowait()
                    steering_text = steering_data["content"]
                    steering_sender = steering_data["sender"]
                except asyncio.QueueEmpty:
                    steering_text = None

                if steering_text:
                    await self.on_step("steering_message", f"{steering_sender}: {steering_text}")
                    current_input = f"[Team steering message from {steering_sender}: {steering_text}]\n\n{current_input}"

            # If we exited the for loop without TASK_COMPLETE (max_steps reached), mark complete
            if not self.completed:
                self.completed = True
                await self.on_step("agent_thought", "Session complete.")