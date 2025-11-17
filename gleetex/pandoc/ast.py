"""Pandoc AST element representations.

Encapsulates and abstracts away the internals of constructing and manipulating
Pandoc's JSON AST as needed in this package. The definitions are heavily
inspired by Pandoc's Haskell type definitions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


# Abstract classes #############################################################

class AbstractAstMixin(ABC):
    """The base class for all element utility mixins."""

    @abstractmethod
    def to_json(self):
        """Return the JSON representation of the object using builtin types."""


class AbstractElement(ABC):
    """The minimal common denominator for all AST elements."""

    # One could consider making this a `classmethod` instead.
    @staticmethod
    @abstractmethod
    def pandoc_ast_name():
        """Return the name of the current object's type in Pandoc's AST."""

    @abstractmethod
    def to_json(self):
        """Return the JSON representation of the object using builtin types."""

    def _to_json(self, content):
        """Return a JSON AST element containing `content`.

        The element type is set to the return value of `self.pandoc_ast_name()`.
        Helper method for subclasses to implement `to_json`.
        """
        return {
            "t": self.pandoc_ast_name(),
            "c": content,
        }


class AbstractBlock(AbstractElement, ABC):
    """A block element."""


class AbstractInline(AbstractElement, ABC):
    """An inline element within a block."""


# Utility mixins ###############################################################

@dataclass(kw_only=True)
class AttributesMixin(AbstractAstMixin):
    """An attribute set consisting of an ID, classes and key-value pairs."""

    id: str = ""
    classes: list[str] = field(default_factory=list)
    key_values: dict[str, str] = field(default_factory=dict)

    def to_json(self):
        return [
            self.id,
            self.classes,
            list(map(list, self.key_values.items())),
        ]


@dataclass(kw_only=True)
class TargetMixin(AbstractAstMixin):
    """The target `url` of a resource (e.g. link or image) titled `title`."""

    url: str = ""
    title: str = ""

    def to_json(self):
        return [self.url, self.title]


@dataclass
class InlinesMixin(AbstractAstMixin):
    """A list of `AbstractInline`s."""

    inlines: list[AbstractInline] = field(default_factory=list)

    def to_json(self):
        return [element.to_json() for element in self.inlines]


class RawFormat(Enum):
    """The types of raw elements."""

    HTML = "html"
    TEX = "tex"

@dataclass
class RawFormatMixin(AbstractAstMixin):
    """The format of a raw element."""

    format: RawFormat

    def to_json(self):
        return self.format.value


# Block elements ###############################################################

@dataclass
class Paragraph(InlinesMixin, AbstractBlock):
    """A block containing inlines."""

    @staticmethod
    def pandoc_ast_name():
        return "Para"

    def to_json(self):
        return self._to_json(super().to_json())


@dataclass
class RawBlock(RawFormatMixin, AbstractBlock):
    """A block containing raw `content` in a certain `format`."""

    content: str = ""

    @staticmethod
    def pandoc_ast_name():
        return "RawBlock"

    def to_json(self):
        return self._to_json([super().to_json(), self.content])


@dataclass
class Heading(InlinesMixin, AttributesMixin, AbstractBlock):
    """A heading block at specified `level`."""

    # The default value is needed here as `dataclass` places this attribute
    # after others with default values.
    level: int = 1

    @staticmethod
    def pandoc_ast_name():
        return "Header"

    def to_json(self):
        return self._to_json(
            [self.level, AttributesMixin.to_json(self), InlinesMixin.to_json(self)]
        )


# Inline elements ##############################################################

@dataclass
class InlineText(AbstractInline):
    """An inline string of text."""

    text: str = ""

    @staticmethod
    def pandoc_ast_name():
        return "Str"

    def to_json(self):
        return self._to_json(self.text)


@dataclass
class InlineCode(AttributesMixin, AbstractInline):
    """Inline verbatim text."""

    code: str = ""

    @staticmethod
    def pandoc_ast_name():
        return "Code"

    def to_json(self):
        return self._to_json([super().to_json(), self.code])


@dataclass
class InlineLink(InlinesMixin, TargetMixin, AttributesMixin, AbstractInline):
    """A link to `url` with `inlines` as alt text."""

    @staticmethod
    def pandoc_ast_name():
        return "Link"

    def to_json(self):
        return self._to_json(
            [
                AttributesMixin.to_json(self),
                InlinesMixin.to_json(self),
                TargetMixin.to_json(self),
            ]
        )


@dataclass
class InlineImage(InlineLink):
    """An image at `url` with `inlines` as alt text."""

    @staticmethod
    def pandoc_ast_name():
        return "Image"


class MathType(Enum):
    """The types of `Math` elements."""

    INLINE = "InlineMath"
    DISPLAY = "DisplayMath"

@dataclass
class Math(AbstractInline):
    """A mathematical formula."""

    formula: str = ""
    type: MathType = MathType.INLINE

    @staticmethod
    def pandoc_ast_name():
        return "Math"

    def to_json(self):
        return self._to_json([{"t": self.type.value}, self.formula])
