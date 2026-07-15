"""Calculator plugin for JARVIS AI assistant."""

import math
import logging
import re
from typing import List, Dict, Any, Optional
from fractions import Fraction

from ..base import BasePlugin

logger = logging.getLogger(__name__)

UNIT_CONVERSIONS = {
    "length": {
        "m": 1.0,
        "km": 1000.0,
        "cm": 0.01,
        "mm": 0.001,
        "mi": 1609.344,
        "yd": 0.9144,
        "ft": 0.3048,
        "in": 0.0254,
    },
    "mass": {
        "kg": 1.0,
        "g": 0.001,
        "mg": 0.000001,
        "lb": 0.453592,
        "oz": 0.0283495,
        "ton": 907.185,
    },
    "temperature": {
        "c": "celsius",
        "f": "fahrenheit",
        "k": "kelvin",
    },
    "volume": {
        "l": 1.0,
        "ml": 0.001,
        "gal": 3.78541,
        "qt": 0.946353,
        "pt": 0.473176,
        "cup": 0.236588,
        "fl_oz": 0.0295735,
    },
    "speed": {
        "m/s": 1.0,
        "km/h": 0.277778,
        "mph": 0.44704,
        "knot": 0.514444,
    },
    "time": {
        "s": 1.0,
        "min": 60.0,
        "hr": 3600.0,
        "day": 86400.0,
        "week": 604800.0,
    },
}

SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "int": int,
    "float": float,
    "max": max,
    "min": min,
    "sum": sum,
    "pow": pow,
    "sqrt": math.sqrt,
    "cbrt": lambda x: x ** (1/3),
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "radians": math.radians,
    "degrees": math.degrees,
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
    "nan": math.nan,
}


class CalculatorPlugin(BasePlugin):
    """Calculator and unit conversion plugin."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Mathematical calculations and unit conversions"

    @property
    def author(self) -> str:
        return "JARVIS Team"

    def __init__(self):
        super().__init__()
        self._history: List[Dict[str, Any]] = []
        self._max_history = 100

    async def initialize(self) -> None:
        await super().initialize()

    async def execute(self, action: str, **kwargs) -> Any:
        """Execute calculator action."""
        actions = {
            "evaluate": self.evaluate,
            "scientific": self.scientific_calculate,
            "convert": self.unit_convert
        }

        handler = actions.get(action)
        if handler:
            return await handler(**kwargs)

        raise ValueError(f"Unknown action: {action}")

    def get_capabilities(self) -> List[str]:
        return ["evaluate", "scientific", "unit_convert"]

    async def evaluate(self, expression: str) -> Dict[str, Any]:
        """Evaluate mathematical expression."""
        try:
            sanitized = self._sanitize_expression(expression)
            result = self._safe_eval(sanitized)

            entry = {
                "expression": expression,
                "result": result,
                "timestamp": self._get_timestamp()
            }
            self._history.append(entry)
            if len(self._history) > self._max_history:
                self._history.pop(0)

            return {
                "success": True,
                "expression": expression,
                "result": result,
                "formatted": self._format_result(result)
            }

        except Exception as e:
            return {
                "success": False,
                "expression": expression,
                "error": str(e)
            }

    async def scientific_calculate(self, expression: str) -> Dict[str, Any]:
        """Evaluate scientific expression with advanced functions."""
        try:
            sanitized = self._sanitize_expression(expression)
            result = self._safe_eval(sanitized, scientific=True)

            entry = {
                "expression": expression,
                "result": result,
                "type": "scientific",
                "timestamp": self._get_timestamp()
            }
            self._history.append(entry)

            return {
                "success": True,
                "expression": expression,
                "result": result,
                "formatted": self._format_result(result),
                "type": "scientific"
            }

        except Exception as e:
            return {
                "success": False,
                "expression": expression,
                "error": str(e)
            }

    async def unit_convert(
        self,
        value: float,
        from_unit: str,
        to_unit: str
    ) -> Dict[str, Any]:
        """Convert between units."""
        try:
            from_unit = from_unit.lower()
            to_unit = to_unit.lower()

            result = self._convert_temperature(value, from_unit, to_unit)
            if result is not None:
                return {
                    "success": True,
                    "value": value,
                    "from_unit": from_unit,
                    "to_unit": to_unit,
                    "result": result,
                    "formatted": f"{value} {from_unit} = {self._format_result(result)} {to_unit}"
                }

            category = self._find_unit_category(from_unit, to_unit)
            if category is None:
                return {
                    "success": False,
                    "error": f"Cannot convert between {from_unit} and {to_unit}"
                }

            units = UNIT_CONVERSIONS[category]
            if from_unit not in units or to_unit not in units:
                return {
                    "success": False,
                    "error": f"Unknown unit: {from_unit} or {to_unit}"
                }

            base_value = value * units[from_unit]
            result = base_value / units[to_unit]

            return {
                "success": True,
                "value": value,
                "from_unit": from_unit,
                "to_unit": to_unit,
                "result": result,
                "formatted": f"{value} {from_unit} = {self._format_result(result)} {to_unit}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _sanitize_expression(self, expression: str) -> str:
        """Sanitize mathematical expression."""
        sanitized = expression.replace("^", "**")

        sanitized = re.sub(r'(\d)(\()', r'\1*\2', sanitized)
        sanitized = re.sub(r'(\))(\d)', r'\1*\2', sanitized)
        sanitized = re.sub(r'(\))(\()', r'\1*\2', sanitized)

        sanitized = sanitized.replace("×", "*")
        sanitized = sanitized.replace("÷", "/")
        sanitized = sanitized.replace("−", "-")

        return sanitized

    def _safe_eval(self, expression: str, scientific: bool = False) -> float:
        """Safely evaluate mathematical expression."""
        allowed = {**SAFE_FUNCTIONS}
        if scientific:
            allowed.update({
                "comb": math.comb,
                "perm": math.perm,
                "erf": math.erf,
                "gamma": math.gamma,
                "lgamma": math.lgamma,
            })

        compiled = compile(expression, "<expr>", "eval")

        for name in compiled.co_names:
            if name not in allowed:
                raise ValueError(f"Function not allowed: {name}")

        return eval(compiled, {"__builtins__": {}}, allowed)

    def _convert_temperature(
        self,
        value: float,
        from_unit: str,
        to_unit: str
    ) -> Optional[float]:
        """Convert temperature units."""
        temp_units = {"c", "f", "k", "celsius", "fahrenheit", "kelvin"}

        from_normalized = "c" if from_unit.startswith("c") else \
                          "f" if from_unit.startswith("f") else \
                          "k" if from_unit.startswith("k") else None

        to_normalized = "c" if to_unit.startswith("c") else \
                        "f" if to_unit.startswith("f") else \
                        "k" if to_unit.startswith("k") else None

        if from_normalized is None or to_normalized is None:
            return None
        if from_normalized == to_normalized:
            return value

        celsius = value
        if from_normalized == "f":
            celsius = (value - 32) * 5 / 9
        elif from_normalized == "k":
            celsius = value - 273.15

        if to_normalized == "f":
            return celsius * 9 / 5 + 32
        elif to_normalized == "k":
            return celsius + 273.15
        else:
            return celsius

    def _find_unit_category(
        self,
        from_unit: str,
        to_unit: str
    ) -> Optional[str]:
        """Find the category containing both units."""
        for category, units in UNIT_CONVERSIONS.items():
            if from_unit in units and to_unit in units:
                return category
        return None

    def _format_result(self, result: float) -> str:
        """Format numerical result for display."""
        if isinstance(result, float):
            if result == int(result) and abs(result) < 1e15:
                return str(int(result))
            elif abs(result) < 0.0001 or abs(result) > 1e10:
                return f"{result:.6e}"
            else:
                return f"{result:.10g}"
        return str(result)

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get calculation history."""
        return self._history[-limit:]

    def clear_history(self) -> None:
        """Clear calculation history."""
        self._history.clear()

    async def on_command(self, command: str, args: Optional[Dict] = None) -> Optional[str]:
        """Handle calculator commands."""
        if command == "calc":
            expression = args.get("expression", "") if args else ""
            if not expression:
                return "Please provide a mathematical expression"

            result = await self.evaluate(expression)
            if result["success"]:
                return f"{result['expression']} = {result['formatted']}"
            else:
                return f"Error: {result['error']}"

        elif command == "convert":
            if not args:
                return "Usage: convert <value> <from_unit> to <to_unit>"

            value = args.get("value", 0)
            from_unit = args.get("from_unit", "")
            to_unit = args.get("to_unit", "")

            result = await self.unit_convert(float(value), from_unit, to_unit)
            if result["success"]:
                return result["formatted"]
            else:
                return f"Error: {result['error']}"

        return None
