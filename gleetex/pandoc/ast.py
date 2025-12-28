"""Pandoc AST element representations.

Encapsulates and abstracts away the internals of constructing and manipulating
Pandoc's JSON AST as needed in this package. The definitions are heavily
inspired by Pandoc's Haskell type definitions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
# Using `StrEnum` instead of plain `Enum` enables seamless usage of the enum
# values in JSON (treated as plain `str`) and in code while preserving most of
# an `Enum`s advantages.
from enum import StrEnum

from ..parser import ParseException


# Constants ####################################################################

# A `list` is used here as this eases the comparison to the `list` used in
# Pandoc's JSON AST. We only support a single minor version (currently the
# latest) as Pandoc's AST API seems to break between minor versions, but these
# changes occur rarely.
SUPPORTED_AST_VERSION = [1, 23]
"""The Pandoc JSON AST version supported for parsing by this module."""


# Exceptions ###################################################################

# Using `ParseException` as superclass as it is handled properly in global
# parsing exception handling.
class PandocJsonAstParseError(ParseException):
    """Invalid or unknown structure encountered while parsing a Pandoc JSON AST.

    Attributes:

    - `msg`: A message describing the exact error encountered.
    - `ast`: The AST where the error encountered.
    """

    def __init__(self, msg, ast):
        super().__init__(msg)
        self.ast = ast

    def __str__(self):
        """Return a prepared error description including `ast` and `msg`."""
        return f"Error while parsing Pandoc AST `{self.ast}`: {self.msg}"


class UnsupportedPandocJsonAstVersionError(PandocJsonAstParseError):
    """An unsupported version of Pandoc's JSON AST was encountered.

    Additional attribute:

    - `version`: The unsupported version encountered (changing its value will
      not change `msg`).
    """

    def __init__(self, version, ast):
        super().__init__(
            f"Unsupported AST version `{version}`;"
            f" only `{SUPPORTED_AST_VERSION}` is supported",
            ast,
        )
        # NOTE: When this attribute is changed later, `msg` will not match.
        self.version = version


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

    # This method provides the foundation for a potential complete AST parsing
    # in the future.
    @classmethod
    def _content_from_json(cls, json_ast):
        """Return the element JSON content of the `json_ast` element.

        `json_ast` should be an element of this type (`cls`), if not or any
        other error is encountered, a `PandocJsonAstParseError` is raised.

        This method is intended to be used in subclasses when constructing
        themselves from a JSON AST node.
        """
        match json_ast:
            case {"t": ast_type, "c": content} if ast_type == cls.pandoc_ast_name():
                return content
            case _:
                raise PandocJsonAstParseError(
                    "Unknown or invalid AST node", json_ast
                )


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


class RawFormat(StrEnum):
    """The types of raw elements."""

    HTML = "html"
    TEX = "tex"

@dataclass
class RawFormatMixin(AbstractAstMixin):
    """The format of a raw element."""

    format: RawFormat

    def to_json(self):
        return self.format


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


class MathType(StrEnum):
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
        return self._to_json([{"t": self.type}, self.formula])

    # This mechanism could be generalized (in an abstract super class) when
    # implemented similarly in another element type.
    @classmethod
    def from_json(cls, json_ast):
        """Construct a `Math` element from the Pandoc `json_ast` node."""
        match cls._content_from_json(json_ast):
            case [{"t": math_type}, formula] if math_type in MathType:
                return cls(formula, MathType(math_type))
            case _:
                # More cases could be added in order to improve the error
                # message, but in order to remain simple and in the assumption
                # that this error is rarely encountered, we refrain from doing
                # so.
                raise PandocJsonAstParseError(
                    f"Invalid or unknown AST for `{cls.pandoc_ast_name()}` element",
                    json_ast,
                )


# Utility functions ############################################################

def foreach_element(element_type, action, ast):
    """Perform `action` recursively for each `element_type` element in `ast`.

    `ast` should be a (valid) Pandoc JSON AST node or a `list` of such and
    `element_type` a (non-abstract) subclass of `AbstractElement`. If any
    unknown element type or structure in `ast` is encountered while traversing,
    it is silently ignored.

    `action` should be a function that takes a raw Pandoc JSON AST element as
    input and returns either such an element as output, which will replace the
    original element in `ast`, or `None`, where the passed element is left
    untouched.
    """
    # The following implements a simple traversing algorithm based on simple
    # parsing assumptions of the structure of the Pandoc JSON AST in order
    # to stay simple and not to have to implement every possible AST element
    # type for correct AST parsing.
    #
    # For similar reasons, we don't construct an instance of `element_type` of
    # the found AST nodes as this would require support for at least every
    # supported element type and thus incur high overhead that we might never
    # actually need (currently, we only ever construct `Math` elements).
    match ast:
        case [*_]:
            for element in ast:
                foreach_element(element_type, action, element)
        case {"t": type} if type == element_type.pandoc_ast_name():
            if (new_ast := action(ast)) is not None:
                ast.clear()
                ast.update(new_ast)
        case {"c": content}:
            foreach_element(element_type, action, content)
        # Silently ignore any unknown case.


def is_supported_ast_version(version):
    """Return whether `version` is supported for parsing in this module.

    `version` should be a `list` of at least two integers which are compared
    for equality with `SUPPORTED_AST_VERSION`; the return value is `True` if
    `version` is supported, else `False`. If `version` is of an unexpected
    format, an exception will be raised.
    """
    # Not following semantic versioning semantics as Pandoc's AST API seems to
    # break between minor versions.
    return version[:2] == SUPPORTED_AST_VERSION


def ast_root_blocks(ast_root):
    """Return the blocks of the Pandoc JSON `ast_root`.

    If `ast_version` is an invalid or unknown Pandoc JSON AST root, a
    `PandocJsonAstParseError` is raised. Else, the version of `ast_root` is
    checked against `SUPPORTED_AST_VERSION` and if unsupported, a
    `UnsupportedPandocJsonAstVersionError` is raised. If it is supportede, the
    block elements are returned *without copying*, so any modification will
    propagate to `ast_root`.
    """
    match ast_root:
        case {"pandoc-api-version": [*_] as version, "blocks": [*_] as blocks}:
            if is_supported_ast_version(version):
                return blocks
            else:
                raise UnsupportedPandocJsonAstVersionError(
                    # Patch `"blocks"` in order not to print the entire possibly
                    # gigantic AST on error.
                    version, ast_root | {"blocks": "[...]"}
                )
        case _:
            raise PandocJsonAstParseError(
                "Invalid or unknown Pandoc JSON AST root", ast_root
            )
