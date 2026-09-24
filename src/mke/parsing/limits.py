"""Configurable limits for the Safe Mathematical Parser."""

from pydantic import BaseModel, Field


class ParserLimits(BaseModel):
    """Resource bounds for parsing and intermediate expressions to prevent DoS."""

    max_input_length: int = Field(default=300, description="Max raw input character count")
    max_tokens: int = Field(default=150, description="Max token count")
    max_ast_depth: int = Field(default=15, description="Max depth of the AST")
    max_node_count: int = Field(default=250, description="Max total AST nodes")
    max_coefficient_magnitude: int = Field(
        default=10**9, description="Max absolute value of integer coefficients"
    )
    max_exponent: int = Field(
        default=4, description="Max non-negative integer exponent allowed on caret"
    )
    max_polynomial_degree: int = Field(
        default=4, description="Max degree of normalized polynomials"
    )


DEFAULT_LIMITS = ParserLimits()
