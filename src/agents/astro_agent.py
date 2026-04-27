"""
Astro Bot Agent

Specialization: general_assistant
Provider: Gemini S2 Model
Capabilities: General assistance, navigation, context awareness, webhook integration
"""

from src.agents.gemini_agent import GeminiAgent
from src.agents.base_agent import AgentType, AgentCapability

class AstroAgent(GeminiAgent):
    def __init__(self):
        super().__init__(
            name="AstroBot",
            specialization="general_assistant",
            agent_type=AgentType.MAIN,
            description="A general-purpose AI assistant capable of helping with various tasks and navigating the platform.",
            capabilities=[
                AgentCapability(name="general_assistance", description="Provides general information and help."),
                AgentCapability(name="platform_navigation", description="Helps users navigate to different sections of the platform."),
                AgentCapability(name="context_awareness", description="Understands context across different pages and agents."),
                AgentCapability(name="webhook_integration", description="Can interact with external systems via webhooks."),
                AgentCapability(name="cli_interface", description="Responds to command-line like inputs."),
            ]
        )

    async def handle_message(self, message):
        # Implement Astro Bot's general message handling logic here.
        # This could include intent recognition for navigation, general Q&A, etc.
        response_content = f"AstroBot received your message: '{message.content}'. I am a general assistant. How can I help you today?"
        if "finance dashboard" in message.content.lower():
            response_content += "\n\nNavigating to Finance Dashboard..."
            # In a real implementation, this would trigger a client-side navigation.
        return self.create_response(message, response_content)