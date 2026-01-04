"""
STARK Code Explanation
=======================
Explain code functionality, patterns, and logic in clear terms.

Module 7 of 9 - Capabilities
"""

import re
import ast
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Design patterns that can be detected."""
    SINGLETON = "singleton"
    FACTORY = "factory"
    DECORATOR = "decorator"
    OBSERVER = "observer"
    ITERATOR = "iterator"
    CONTEXT_MANAGER = "context_manager"
    MIXIN = "mixin"
    UNKNOWN = "unknown"


@dataclass
class CodeAnalysis:
    """Result of code analysis."""
    summary: str
    purpose: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    patterns: List[PatternType] = field(default_factory=list)
    complexity: str = "medium"  # low, medium, high
    walkthrough: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "purpose": self.purpose,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "patterns": [p.value for p in self.patterns],
            "complexity": self.complexity,
            "walkthrough": self.walkthrough,
            "suggestions": self.suggestions,
        }


class CodeExplainer:
    """
    Explain code in clear, understandable terms.
    
    Features:
    - Function/class purpose identification
    - Step-by-step walkthrough
    - Design pattern recognition
    - Complexity assessment
    - Improvement suggestions
    
    Usage:
        explainer = CodeExplainer()
        analysis = explainer.explain(code_string)
        print(analysis.summary)
        for step in analysis.walkthrough:
            print(step)
    """
    
    # Pattern detection signatures
    PATTERN_SIGNATURES = {
        PatternType.SINGLETON: [
            r"_instance\s*=\s*None",
            r"def\s+get_instance\s*\(",
            r"cls\._instance\s*is\s*None",
        ],
        PatternType.FACTORY: [
            r"def\s+create_\w+\s*\(",
            r"def\s+make_\w+\s*\(",
            r"return\s+\w+\(",
        ],
        PatternType.DECORATOR: [
            r"@\w+",
            r"def\s+\w+\s*\(\s*func\s*\)",
            r"functools\.wraps",
        ],
        PatternType.CONTEXT_MANAGER: [
            r"def\s+__enter__\s*\(",
            r"def\s+__exit__\s*\(",
            r"@contextmanager",
        ],
        PatternType.ITERATOR: [
            r"def\s+__iter__\s*\(",
            r"def\s+__next__\s*\(",
            r"yield\s+",
        ],
    }
    
    def __init__(self):
        """Initialize code explainer."""
        self._analysis_count = 0
        logger.info("CodeExplainer initialized")
    
    def explain(self, code: str) -> CodeAnalysis:
        """
        Analyze and explain code.
        
        Args:
            code: Python code string
            
        Returns:
            CodeAnalysis with explanation
        """
        self._analysis_count += 1
        
        # Parse code
        tree = self._parse_code(code)
        
        # Extract information
        summary = self._generate_summary(code, tree)
        purpose = self._identify_purpose(code, tree)
        inputs, outputs = self._extract_io(code, tree)
        patterns = self._detect_patterns(code)
        complexity = self._assess_complexity(code, tree)
        walkthrough = self._generate_walkthrough(code, tree)
        suggestions = self._generate_suggestions(code, tree, complexity)
        
        return CodeAnalysis(
            summary=summary,
            purpose=purpose,
            inputs=inputs,
            outputs=outputs,
            patterns=patterns,
            complexity=complexity,
            walkthrough=walkthrough,
            suggestions=suggestions,
        )
    
    def _parse_code(self, code: str) -> Optional[ast.AST]:
        """Parse code to AST."""
        try:
            return ast.parse(code)
        except SyntaxError as e:
            logger.warning(f"Failed to parse code: {e}")
            return None
    
    def _generate_summary(self, code: str, tree: Optional[ast.AST]) -> str:
        """Generate a brief summary."""
        if tree is None:
            return "Code could not be parsed (syntax error)"
        
        # Count elements
        functions = []
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
        
        parts = []
        
        if classes:
            parts.append(f"Defines {len(classes)} class(es): {', '.join(classes[:3])}")
        
        if functions:
            # Filter out class methods
            top_functions = [f for f in functions if not f.startswith("_") or f == "__init__"][:3]
            if top_functions:
                parts.append(f"Contains {len(functions)} function(s): {', '.join(top_functions)}")
        
        if not parts:
            lines = len(code.strip().split("\n"))
            parts.append(f"Code snippet with {lines} lines")
        
        return ". ".join(parts)
    
    def _identify_purpose(self, code: str, tree: Optional[ast.AST]) -> str:
        """Identify the main purpose of the code."""
        if tree is None:
            return "Unknown (parsing failed)"
        
        # Check for docstring
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                docstring = ast.get_docstring(node)
                if docstring:
                    # Return first sentence of docstring
                    first_sentence = docstring.split("\n")[0].strip()
                    if first_sentence:
                        return first_sentence
        
        # Infer from function/class names
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                return f"Implements the {node.name} class"
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                return f"Implements the {node.name} function"
        
        return "General utility code"
    
    def _extract_io(
        self,
        code: str,
        tree: Optional[ast.AST],
    ) -> Tuple[List[str], List[str]]:
        """Extract inputs and outputs."""
        inputs = []
        outputs = []
        
        if tree is None:
            return inputs, outputs
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Get arguments
                for arg in node.args.args:
                    if arg.arg != "self":
                        annotation = ""
                        if arg.annotation:
                            annotation = f": {ast.unparse(arg.annotation)}"
                        inputs.append(f"`{arg.arg}{annotation}`")
                
                # Check for return
                if node.returns:
                    outputs.append(f"`{ast.unparse(node.returns)}`")
                
                # Check for return statements
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and child.value:
                        if not outputs:
                            outputs.append("Returns a value")
        
        return inputs[:5], outputs[:3]  # Limit
    
    def _detect_patterns(self, code: str) -> List[PatternType]:
        """Detect design patterns in code."""
        patterns = []
        
        for pattern, signatures in self.PATTERN_SIGNATURES.items():
            for sig in signatures:
                if re.search(sig, code):
                    if pattern not in patterns:
                        patterns.append(pattern)
                    break
        
        return patterns
    
    def _assess_complexity(self, code: str, tree: Optional[ast.AST]) -> str:
        """Assess code complexity."""
        if tree is None:
            return "unknown"
        
        # Count complexity indicators
        score = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For)):
                score += 1
            if isinstance(node, ast.Try):
                score += 2
            if isinstance(node, ast.comprehension):
                score += 1
            if isinstance(node, ast.Lambda):
                score += 1
        
        # Line count factor
        lines = len(code.strip().split("\n"))
        if lines > 100:
            score += 3
        elif lines > 50:
            score += 2
        elif lines > 20:
            score += 1
        
        # Classify
        if score <= 3:
            return "low"
        elif score <= 8:
            return "medium"
        else:
            return "high"
    
    def _generate_walkthrough(self, code: str, tree: Optional[ast.AST]) -> List[str]:
        """Generate step-by-step walkthrough."""
        steps = []
        
        if tree is None:
            steps.append("Code could not be parsed for walkthrough")
            return steps
        
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                modules = ", ".join(alias.name for alias in node.names)
                steps.append(f"**Import**: Imports {modules}")
            
            elif isinstance(node, ast.ImportFrom):
                steps.append(f"**Import**: From `{node.module}` imports specific components")
            
            elif isinstance(node, ast.ClassDef):
                bases = ", ".join(ast.unparse(b) for b in node.bases) if node.bases else "object"
                steps.append(f"**Class `{node.name}`**: Defines a class inheriting from {bases}")
                
                # Add method summary
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                if methods:
                    steps.append(f"  - Methods: {', '.join(methods[:5])}")
            
            elif isinstance(node, ast.FunctionDef):
                args = [a.arg for a in node.args.args if a.arg != "self"]
                args_str = ", ".join(args) if args else "no arguments"
                steps.append(f"**Function `{node.name}`**: Takes {args_str}")
                
                docstring = ast.get_docstring(node)
                if docstring:
                    first_line = docstring.split("\n")[0]
                    steps.append(f"  - Purpose: {first_line}")
            
            elif isinstance(node, ast.Assign):
                targets = ", ".join(ast.unparse(t) for t in node.targets)
                steps.append(f"**Assignment**: Sets `{targets}`")
        
        if not steps:
            steps.append("Simple code block with no major structural elements")
        
        return steps[:10]  # Limit to 10 steps
    
    def _generate_suggestions(
        self,
        code: str,
        tree: Optional[ast.AST],
        complexity: str,
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        if tree is None:
            suggestions.append("Fix syntax errors before analysis")
            return suggestions
        
        # Check for missing docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    suggestions.append(f"Add a docstring to `{node.name}`")
                    break
        
        # Check for type hints
        has_hints = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.returns or any(a.annotation for a in node.args.args):
                    has_hints = True
                    break
        
        if not has_hints:
            suggestions.append("Consider adding type hints for better code clarity")
        
        # Complexity suggestion
        if complexity == "high":
            suggestions.append("Consider breaking down complex logic into smaller functions")
        
        # Long lines
        lines = code.split("\n")
        long_lines = sum(1 for l in lines if len(l) > 100)
        if long_lines > 3:
            suggestions.append("Some lines are very long - consider breaking them up")
        
        # Magic numbers
        if re.search(r'(?<!["\'])\b\d{3,}\b(?!["\'])', code):
            suggestions.append("Consider using named constants instead of magic numbers")
        
        return suggestions[:5]
    
    def explain_line(self, line: str) -> str:
        """Explain a single line of code."""
        line = line.strip()
        
        # Common patterns
        if line.startswith("def "):
            return "Function definition"
        if line.startswith("class "):
            return "Class definition"
        if line.startswith("import ") or line.startswith("from "):
            return "Import statement"
        if line.startswith("return "):
            return "Return statement - exits function with a value"
        if line.startswith("if "):
            return "Conditional statement - executes block if condition is true"
        if line.startswith("for "):
            return "For loop - iterates over a sequence"
        if line.startswith("while "):
            return "While loop - repeats while condition is true"
        if line.startswith("try:"):
            return "Try block - handles exceptions"
        if "=" in line and not line.startswith("=="):
            return "Assignment statement"
        if line.startswith("#"):
            return "Comment"
        
        return "Python statement"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get explainer statistics."""
        return {
            "total_analyses": self._analysis_count,
        }


# =============================================================================
# FACTORY
# =============================================================================

_explainer_instance: Optional[CodeExplainer] = None


def get_code_explainer() -> CodeExplainer:
    """Get or create the global code explainer."""
    global _explainer_instance
    
    if _explainer_instance is None:
        _explainer_instance = CodeExplainer()
    
    return _explainer_instance
