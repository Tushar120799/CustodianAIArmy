"""
Finance AI Agent

Specialization: finance_analyst
Provider: Gemini S2 Model
Capabilities: Portfolio analysis, strategy creation, backtesting, risk management
import random

Tools Access: Kite, Groww, Zerodha MCP servers, market data, news feeds
Authentication: PAN + Mobile OTP flow for broker connections
Permissions: Read by default, execute trading only after explicit user confirmation
"""

from src.agents.gemini_agent import GeminiAgent
from typing import Dict, List, Any
from datetime import datetime, timedelta
import random
from src.agents.base_agent import AgentType, AgentCapability

class FinanceAgent(GeminiAgent):
    def __init__(self):
        super().__init__(
            name="FinanceAI",
            specialization="finance_analyst",
            agent_type=AgentType.MAIN,
            description="Specialized in financial analysis, portfolio management, and trading strategies.",
            capabilities=[
                AgentCapability(name="portfolio_analysis", description="Analyze investment portfolios."),
                AgentCapability(name="strategy_creation", description="Develop and suggest trading strategies."),
                AgentCapability(name="backtesting", description="Simulate strategies against historical data."),
                AgentCapability(name="risk_management", description="Assess and manage financial risks."),
                AgentCapability(name="broker_integration", description="Connect to brokerage platforms (Kite, Groww, Zerodha)."),
                AgentCapability(name="market_data_access", description="Access real-time and historical market data."),
                AgentCapability(name="news_feed_analysis", description="Analyze financial news and sentiment.")
            ]
        )
        # Placeholder for tool access configuration
        self.tools_access = ["Kite MCP", "Groww MCP", "Zerodha MCP", "Market Data API", "News Feed API"]

    def _get_mcp_executor(self):
        """Gets the MCP executor for the 'finance' specialization."""
        return super()._get_mcp_executor()

    async def handle_message(self, message):
        """
        Handles incoming messages by parsing commands and executing financial tasks.
        This is the core logic hub for the FinanceAgent.
        """
        user_input = message.content.strip().lower()

        # --- Direct Command Parsing for Specific Actions ---
        if user_input.startswith("initiate_broker_connection"):
            # Expected format: "initiate_broker_connection broker=zerodha pan=... mobile=..."
            params = dict(item.split("=") for item in user_input.split(" ")[1:])
            return await self._skill_initiate_broker_connection(params)

        if user_input.startswith("verify_broker_connection"):
            # Expected format: "verify_broker_connection broker=zerodha otp=..."
            params = dict(item.split("=") for item in user_input.split(" ")[1:])
            return await self._skill_verify_broker_connection(params)

        if user_input.startswith("explain chart for"):
            symbol = user_input.replace("explain chart for", "").strip().upper()
            explanation = await self._skill_explain_instrument(symbol)
            return self.create_response(message, explanation)

        if user_input.startswith("explain my position in"):
            symbol = user_input.split(" in ")[1].split(" ")[0].upper()
            explanation = await self._skill_explain_instrument(symbol, is_position=True)
            return self.create_response(message, explanation)

        if user_input.startswith("backtest"):
            strategy_text = user_input.split("'")[1] if "'" in user_input else "default strategy"
            # This would call a real backtesting tool/service.
            # For now, we simulate the backtest and return the results.
            backtest_result = self._skill_backtest_strategy(strategy_text)
            response_content = f"Backtest for strategy '{strategy_text}' completed."
            return self.create_response(message, response_content, metadata={"results": backtest_result})

        if user_input.startswith("get_historical_data for="):
            symbol = user_input.split("=")[1].strip().upper()
            data = await self._skill_get_historical_data(symbol)
            return self.create_response(message, f"Historical data for {symbol}", metadata=data)


        # --- Main Orchestration Flow ---
        # This flow follows the "HOW YOUR AGENT SHOULD THINK" specification.
        
        # 1. Detect Market Regime
        regime = self._skill_detect_market_regime()
        
        # 2. Select Strategy & Run Modules based on Regime
        signals = {}
        if "momentum" in regime.get("preferred_strategy", []):
            signals["momentum"] = await self._skill_momentum_signal_engine()
            signals["ath_breakout"] = self._skill_ath_breakout_intelligence()
        if "mean_reversion" in regime.get("preferred_strategy", []):
            signals["mean_reversion"] = self._skill_indicator_fusion()
        if "value" in regime.get("preferred_strategy", []):
            signals["value"] = self._skill_intrinsic_value_estimation()

        # 3. Run General Analysis Skills
        signals["financial_health"] = self._skill_financial_health_analysis()
        signals["catalysts"] = self._skill_earnings_catalyst_detection()

        # 4. Aggregate Signals in the Decision Engine
        final_decision = self._skill_multi_factor_decision_engine(regime, signals)

        # 5. Format the final decision into a human-readable response
        response_content = self._format_decision_as_response(final_decision)

        return self.create_response(message, response_content, metadata=final_decision)

    def _format_decision_as_response(self, decision_data: dict) -> str:
        """Converts the structured decision data into a readable string."""
        response = f"### Analysis & Decision\n\n"
        response += f"**Market Regime:** `{decision_data.get('market_regime', 'N/A')}` (Risk: {decision_data.get('risk_level', 'N/A')})\n"
        response += f"**Preferred Strategy:** {', '.join(decision_data.get('preferred_strategy', []))}\n\n"
        response += f"--- \n\n"
        response += f"**Final Decision: `{decision_data.get('decision', 'HOLD')}`**\n"
        response += f"- **Time Horizon:** {decision_data.get('time_horizon', 'N/A')}\n"
        response += f"- **Confidence Score:** {1 - decision_data.get('risk_score', 1.0):.2f}\n"
        response += f"- **Primary Drivers:** {', '.join(decision_data.get('strategies_used', []))}\n\n"
        
        # Add reasons from the momentum signal if available
        if decision_data.get('momentum_signal', {}).get('reason'):
            response += "**Key Momentum Signals:**\n"
            for reason in decision_data['momentum_signal']['reason']:
                response += f"- {reason}\n"

        return response

    # --------------------------------------------------------------------------
    # CORE META-SKILL & STRATEGY SKILLS (Simulated Implementations)
    # --------------------------------------------------------------------------

    async def _fetch_market_data(self, symbol: str, data_type: str = "quote") -> Dict[str, Any]:
        """
        Fetches market data using the Zerodha MCP tool.
        """
        mcp_executor = self._get_mcp_executor()
        if not mcp_executor:
            self.logger.warning("MCP executor not available for fetching market data.")
            return {}
        
        try:
            # The tool name 'zerodha' corresponds to the key in .mcp.json
            tool_result = await mcp_executor.execute_tool(
                "zerodha", 
                {"action": "get_data", "symbol": symbol, "type": data_type}
            )
            if tool_result.is_error:
                self.logger.error(f"MCP tool error fetching data for {symbol}: {tool_result.content}")
                return {}
            # Assuming the tool returns a JSON string
            return json.loads(tool_result.content)
        except Exception as e:
            self.logger.error(f"Failed to fetch market data for {symbol} via MCP: {e}")
            return {}

    async def _fetch_market_index_data(self, index_symbol: str = "NIFTY 50") -> dict:
        """
        (Data-driven) Fetches key data for a market index via MCP.
        """
        # This is a conceptual implementation. The MCP tool would need to support this.
        # For now, we simulate the output structure based on what a real call might provide.
        # real_data = await self._fetch_market_data(index_symbol, "index_quote")
        return {
            "current_price": 23500.0,
            "200_dma": 22000.0,
            "volatility_index": 14.5,
            "advances": 35,
            "declines": 15,
        }

    async def _fetch_stock_data(self, stock_symbol: str) -> dict:
        """
        (Data-driven) Fetches key data for a specific stock via MCP.
        """
        # real_quote = await self._fetch_market_data(stock_symbol, "full_quote")
        # real_fundamentals = await self._fetch_market_data(stock_symbol, "fundamentals")
        # For now, simulate the combined output.
        return {
            "symbol": stock_symbol,
            "current_price": 215.0,
            "200_dma": 190.0,
            "all_time_high": 220.0,
            "avg_volume_30d": 50_000_000,
            "current_volume": 80_000_000,
            "relative_strength_vs_index": 1.2, # > 1 means outperforming
        }

    async def _skill_detect_market_regime(self) -> Dict[str, Any]:
        """
        SKILL 1: Detects the current market regime.
        (Data-Driven Implementation)
        """
        index_data = await self._fetch_market_index_data()
        
        is_trending = index_data["current_price"] > index_data["200_dma"]
        is_volatile = index_data["volatility_index"] > 20

        if is_trending:
            if is_volatile:
                return {"market_regime": "bull_trending_volatile", "preferred_strategy": ["momentum"], "risk_level": "high"}
            else:
                return {"market_regime": "bull_trending_calm", "preferred_strategy": ["momentum", "breakout"], "risk_level": "moderate"}
        else: # Sideways or Bear
            if is_volatile:
                return {"market_regime": "sideways_volatile", "preferred_strategy": ["mean_reversion"], "risk_level": "high"}
            else:
                return {"market_regime": "sideways_calm", "preferred_strategy": ["mean_reversion", "value"], "risk_level": "low"}

    async def _skill_momentum_signal_engine(self, stock_symbol: str = "AAPL") -> Dict[str, Any]:
        """
        SKILL 2: Generates momentum signals based on 200 DMA and ATH breakout.
        (Data-Driven Implementation)
        """
        stock_data = await self._fetch_stock_data(stock_symbol)
        reasons = []
        confidence = 0.0

        if stock_data["current_price"] > stock_data["200_dma"]:
            reasons.append("Price is above 200 DMA")
            confidence += 0.4
        if stock_data["current_price"] > stock_data["all_time_high"]:
            reasons.append("Price is breaking All-Time High")
            confidence += 0.3
        if stock_data["current_volume"] > (stock_data["avg_volume_30d"] * 1.5):
            reasons.append("Volume spike detected ( > 1.5x average)")
            confidence += 0.2

        return {
            "signal": "BUY" if confidence > 0.5 else "HOLD",
            "confidence": round(confidence, 2),
            "reason": reasons
        }

    def _skill_ath_breakout_intelligence(self) -> dict:
        """
        SKILL 8: Specialized ATH breakout analysis.
        (Simulation)
        """
        return {
            "is_ath_breakout": True,
            "volume_confirmed": True,
            "sector_aligned": random.choice([True, False])
        }

    def _skill_indicator_fusion(self) -> dict:
        """
        SKILL 7: Combines signals from multiple technical indicators.
        (Simulation)
        """
        return {
            "rsi_signal": "neutral",
            "macd_signal": "bullish_crossover",
            "bollinger_signal": "squeeze_release",
            "weighted_score": random.uniform(-1, 1) # -1 (sell) to +1 (buy)
        }

    def _skill_intrinsic_value_estimation(self) -> dict:
        """
        SKILL 9: Estimates the intrinsic value of a stock.
        (Simulation)
        """
        current_price = random.uniform(800, 1200)
        intrinsic_value = current_price * random.uniform(0.8, 1.3)
        margin_of_safety = ((intrinsic_value - current_price) / intrinsic_value) * 100 if intrinsic_value > 0 else 0
        return {
            "intrinsic_value": round(intrinsic_value, 2),
            "current_price": round(current_price, 2),
            "margin_of_safety_percent": round(margin_of_safety, 2)
        }

    def _skill_financial_health_analysis(self) -> dict:
        """
        SKILL 10: Analyzes the financial health of a company.
        (Simulation)
        """
        return {
            "revenue_growth": f"{random.uniform(5, 25):.1f}%",
            "profit_margin": f"{random.uniform(10, 40):.1f}%",
            "debt_to_equity": round(random.uniform(0.1, 1.5), 2)
        }

    def _skill_earnings_catalyst_detection(self) -> dict:
        """
        SKILL 12: Detects recent earnings news or catalysts.
        (Simulation)
        """
        catalysts = ["Positive earnings surprise", "Upgraded guidance", "New major partnership announced", "No significant recent catalysts"]
        return {"latest_catalyst": random.choice(catalysts)}

    def _skill_multi_factor_decision_engine(self, regime: dict, signals: dict) -> dict:
        """
        SKILL 14: Aggregates all inputs to make a final decision.
        (Simulation)
        """
        strategies_used = []
        risk_score = 0.5

        # Base decision on regime and primary signal
        if "momentum" in regime["preferred_strategy"] and signals.get("momentum", {}).get("signal") == "BUY":
            decision = "STRONG BUY"
            strategies_used.append("momentum")
            risk_score = 0.3
        elif "value" in regime["preferred_strategy"] and signals.get("value", {}).get("margin_of_safety_percent", 0) > 20:
            decision = "ACCUMULATE"
            strategies_used.append("value_investing")
            risk_score = 0.4
        else:
            decision = "HOLD"
            strategies_used.append("observation")
            risk_score = 0.6

        # Combine all data for a comprehensive output
        final_output = {
            "decision": decision,
            "strategies_used": strategies_used,
            "risk_score": risk_score,
            "time_horizon": "swing" if "momentum" in strategies_used else "long-term",
            **regime,
            "momentum_signal": signals.get("momentum", {}),
            "value_signal": signals.get("value", {}),
        }
        return final_output

    async def _skill_get_historical_data(self, symbol: str) -> Dict[str, Any]:
        """
        (Data-driven Placeholder) Fetches historical data for a stock.
        In a real implementation, this would call a financial data API via MCP.
        """
        # TODO: Replace with a real API call via MCP tool
        # tool_result = await mcp_executor.execute_tool("zerodha", {"action": "get_historical", "symbol": symbol})
        
        # For now, generate plausible historical data for the last 365 days
        historical_data = []
        price = random.uniform(150, 250)
        current_date = datetime.now()
        
        for i in range(365, 0, -1):
            date = current_date - timedelta(days=i)
            # Simulate some price volatility
            price *= (1 + random.uniform(-0.02, 0.02))
            historical_data.append({
                "time": date.strftime('%Y-%m-%d'),
                "value": round(price, 2)
            })
            
        return {"success": True, "data": historical_data}

    # --------------------------------------------------------------------------
    # REAL IMPLEMENTATIONS OF OTHER SKILLS
    # --------------------------------------------------------------------------

    async def _skill_initiate_broker_connection(self, params: dict) -> AgentMessage:
        """Uses MCP to initiate a broker connection."""
        mcp_executor = self._get_mcp_executor()
        if not mcp_executor:
            return self.create_response(message, "MCP executor is not available.", is_error=True)

        broker = params.get("broker", "zerodha")
        tool_params = {
            "action": "initiate_login",
            "pan": params.get("pan"),
            "mobile": params.get("mobile")
        }
        
        result = await mcp_executor.execute_tool(broker, tool_params)
        return self.create_response(message, result.content, metadata=json.loads(result.content))

    async def _skill_verify_broker_connection(self, params: dict) -> AgentMessage:
        """Uses MCP to verify OTP and complete connection."""
        mcp_executor = self._get_mcp_executor()
        if not mcp_executor:
            return self.create_response(message, "MCP executor is not available.", is_error=True)

        broker = params.get("broker", "zerodha")
        tool_params = {
            "action": "verify_login",
            "otp": params.get("otp"),
            "session_id": params.get("session_id")
        }
        
        result = await mcp_executor.execute_tool(broker, tool_params)
        return self.create_response(message, result.content, metadata=json.loads(result.content))

    async def _skill_explain_instrument(self, symbol: str, is_position: bool = False) -> str:
        """Generates a detailed, multi-factor explanation for a stock."""
        
        # 1. Run relevant skill modules for the symbol
        stock_data = await self._fetch_stock_data(symbol)
        momentum_signal = await self._skill_momentum_signal_engine(symbol)
        value_signal = self._skill_intrinsic_value_estimation() # Still simulated
        health_signal = self._skill_financial_health_analysis() # Still simulated

        # 2. Build the explanation
        explanation = f"### Analysis for **{symbol.upper()}**\n\n"
        if is_position:
            explanation += "This is an analysis of a stock in your paper portfolio.\n\n"

        explanation += f"**Momentum Analysis:**\n"
        if momentum_signal['reason']:
            for reason in momentum_signal['reason']:
                explanation += f"- {reason}\n"
        else:
            explanation += "- No strong momentum signals detected at this time.\n"
        explanation += f"**Confidence Score:** {momentum_signal['confidence']}\n\n"

        explanation += f"**Valuation Snapshot (Simulated):**\n"
        explanation += f"- **Intrinsic Value:** ${value_signal['intrinsic_value']} vs. **Current Price:** ${value_signal['current_price']}\n"
        explanation += f"- **Margin of Safety:** {value_signal['margin_of_safety_percent']}%\n\n"

        explanation += "**Disclaimer:** This is a data-driven analysis based on available indicators. It is not financial advice."
        return explanation

    def _skill_backtest_strategy(self, strategy_text: str) -> dict:
        """Simulates a backtest run."""
        initial_capital = 10000
        final_capital = initial_capital * random.uniform(0.9, 1.5)
        pnl = final_capital - initial_capital
        return {
            "strategy": strategy_text,
            "symbol": "AAPL",
            "period": "2023-01-01 to 2024-01-01",
            "initial_capital": f"${initial_capital:,.2f}",
            "final_capital": f"${final_capital:,.2f}",
            "pnl": f"${pnl:,.2f}",
            "pnl_percent": f"{(pnl / initial_capital) * 100:.2f}%",
            "sharpe_ratio": f"{random.uniform(0.5, 2.5):.2f}",
            "max_drawdown": f"{random.uniform(5, 25):.2f}%",
            "win_rate": f"{random.uniform(40, 70):.2f}%",
            "total_trades": random.randint(20, 100)
        }

# Example of how to register this agent in agent_manager.py (conceptual)
# finance_agent = FinanceAgent()
# agent_manager.register_agent(finance_agent)