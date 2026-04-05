"""
Sink functionality for outputs.


GladTeX is capable of writing to different output formats, called a sink. A sink
may parse the source and process the formulas in the document, replacing it with
its converted equivalent. Tis decouples the GleeTeX-internal logic from HTML and
allows using it e.g. as a filter for Pandoc (JSON-encoded).
"""

from abc import ABC, abstractmethod
import enum
import html
import os
import posixpath

EXCLUSION_FILE_NAME = 'excluded-descriptions.html'

__all__ = [
    'EXCLUSION_FILE_NAME',
    'AppendedExcludedFormulaOutput',
    'ExcludedFormulaOutput',
    'ExternalExcludedFormulaOutput',
    'HtmlAppended',
    'HtmlExternalFile',
    'HtmlOutput',
    'PandocOutput',
    'PandocAppended',
    'SinkType',
    'write_excluded_formulas',
]

# Todo: localisation
HTML_TEMPLATE_HEAD = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
  "http://www.w3.org/TR/html4/strict.dtd">
<html>\n<head>
  <meta http-equiv="content-type" content="text/html; charset=UTF-8"/>
  <title>Excluded Formulas</title>
</head><!-- DO NOT MODIFY THIS FILE, IT IS AUTOMATICALLY GENERATED -->
<body>
"""


class SinkType(enum.Enum):
    """The type of sink to use. """
    drop = 0
    html_body = 1
    html_file = 2
    json_file = 3
    inline = 4


class ExcludedFormulaOutput(ABC):
    """Describe where and how excluded formulas should be written."""

    def __init__(self, sink_type):
        self.sink_type = sink_type

    def appends_to_document(self):
        """Return whether formulas are appended to the main document."""
        return False

    def resolve_base_path(self, base_path):
        """Return an output object resolved against `base_path`."""
        return self

    def validate(self):
        """Validate the configured output target."""

    def bind_target(self, target):
        """Return an output object bound to `target`."""
        del target
        return self

    @abstractmethod
    def get_link_destination(self, excluded_label, link_prefix=''):
        """Return the link destination for `excluded_label`."""

    @abstractmethod
    def write_excluded_formulas(self, formatter, excluded_formulas_heading=None):
        """Write excluded formulas using this output configuration."""


class ExternalExcludedFormulaOutput(ExcludedFormulaOutput):
    """Excluded formulas written to an external output."""


class AppendedExcludedFormulaOutput(ExcludedFormulaOutput):
    """Excluded formulas appended to the current document."""

    def appends_to_document(self):
        return True


class HtmlOutput(ExcludedFormulaOutput):
    """Base class for excluded-formula outputs rendered as HTML."""

    def _render_html_entries(self, formatter, with_backlinks):
        entries = []
        for label, formula in formatter.get_excluded().items():
            escaped_formula = html.escape(formula)
            if with_backlinks:
                image_anchor_id = formatter.get_excluded_image_anchor_id(label)
                entries.append(
                    f'<p><a href="#{image_anchor_id}" id="{label}">'
                    f'<pre>{escaped_formula}</pre></a></p>\n',
                )
            else:
                entries.append(f'<a id="{label}"><pre>{escaped_formula}</pre></a>\n')
        return ''.join(entries)


class HtmlExternalFile(HtmlOutput, ExternalExcludedFormulaOutput):
    """Write excluded formulas to a separate HTML file."""

    def __init__(self, exclusion_filename):
        super().__init__(SinkType.html_file)
        self.exclusion_filename = exclusion_filename

    def resolve_base_path(self, base_path):
        if not base_path or posixpath.isabs(self.exclusion_filename):
            return self
        return HtmlExternalFile(posixpath.join(base_path, self.exclusion_filename))

    def validate(self):
        if os.path.exists(self.exclusion_filename) and not os.access(
            self.exclusion_filename, os.W_OK,
        ):
            raise OSError(f'file {self.exclusion_filename} not writable')

    def get_link_destination(self, excluded_label, link_prefix=''):
        exclusion_filelink = posixpath.join(
            link_prefix, self.exclusion_filename,
        ) if link_prefix else self.exclusion_filename
        return f'{exclusion_filelink}#{excluded_label}'

    def write_excluded_formulas(self, formatter, excluded_formulas_heading=None):
        del excluded_formulas_heading
        with open(self.exclusion_filename, 'w', encoding='UTF-8') as file:
            file.write(HTML_TEMPLATE_HEAD)
            file.write(self._render_html_entries(formatter, with_backlinks=False))
            file.write('\n</body>\n</html>\n')
        return None


class HtmlAppended(HtmlOutput, AppendedExcludedFormulaOutput):
    """Append excluded formulas to the generated HTML document."""

    def __init__(self, target=None):
        super().__init__(SinkType.html_body)
        self.target = target

    def bind_target(self, target):
        return HtmlAppended(target)

    def get_link_destination(self, excluded_label, link_prefix=''):
        del link_prefix
        return f'#{excluded_label}'

    def write_excluded_formulas(self, formatter, excluded_formulas_heading=None):
        if self.target is None:
            raise ValueError('HtmlAppended requires a target before writing')
        heading = excluded_formulas_heading or 'Excluded Formulas'
        self.target.write(
            f'<aside><h1>{heading}</h1>\n'
            f'{self._render_html_entries(formatter, with_backlinks=True)}'
            '</aside>'
        )
        return None


class PandocOutput(ExcludedFormulaOutput):
    """Base class for excluded-formula outputs rendered as Pandoc AST."""


class PandocAppended(PandocOutput, AppendedExcludedFormulaOutput):
    """Append excluded formulas to a Pandoc AST."""

    def __init__(self, target=None):
        super().__init__(SinkType.json_file)
        self.target = target

    def bind_target(self, target):
        return PandocAppended(target)

    def get_link_destination(self, excluded_label, link_prefix=''):
        del link_prefix
        return f'#{excluded_label}'

    def write_excluded_formulas(self, formatter, excluded_formulas_heading=None):
        if self.target is None:
            raise ValueError('PandocAppended requires a target before writing')
        from .pandoc.ast import (
            Heading,
            InlineCode,
            InlineLink,
            InlineText,
            Paragraph,
            RawBlock,
            RawFormat,
        )

        heading = excluded_formulas_heading or 'Excluded Formulas'
        formula_paragraphs = [
            Paragraph([
                InlineLink(
                    [InlineCode(formula)],
                    url=f"#{formatter.get_excluded_image_anchor_id(label)}",
                    id=label,
                ),
            ])
            for label, formula in formatter.get_excluded().items()
        ]

        self.target.extend([block.to_json() for block in (
            RawBlock(RawFormat.HTML, "<aside>"),
            Heading([InlineText(heading)], level=1),
            *formula_paragraphs,
            RawBlock(RawFormat.HTML, "</aside>"),
        )])
        return None


def _html_write_excluded_file(exclusion_filename, formatted_excluded_formulas):
    """Backward-compatible helper for the old sink API."""
    output = HtmlExternalFile(exclusion_filename)
    formatter = _LegacyExcludedFormulaFormatter(formatted_excluded_formulas)
    output.write_excluded_formulas(formatter)


def _html_write_excluded_body(exclusion_filename, formatted_excluded_formulas):
    with open(exclusion_filename, 'w', encoding='UTF-8') as file:
        _html_write_excluded(file, formatted_excluded_formulas)


def _html_write_excluded(file_obj, formatted_excluded_formulas):
    for label, formula in formatted_excluded_formulas.items():
        escaped_formula = html.escape(formula)
        file_obj.write(f'<a id="{label}"><pre>{escaped_formula}</pre></a>\n')


# Map the sink type to their processing function.
_EXCLUSION_FORMULA_SINKS = {
    SinkType.html_file: _html_write_excluded_file,
    SinkType.html_body: _html_write_excluded_body,
}


class _LegacyExcludedFormulaFormatter:
    """Adapter used to keep the old `write_excluded_formulas` signature working."""

    def __init__(self, excluded_formulas):
        self._excluded_formulas = excluded_formulas

    def get_excluded(self):
        return self._excluded_formulas

    @staticmethod
    def get_excluded_image_anchor_id(excluded_label):
        return excluded_label


def _write_excluded_formulas_legacy(
    sink_type, exclusion_filename, formatted_excluded_formulas
):
    if not formatted_excluded_formulas:
        return None

    try:
        writer = _EXCLUSION_FORMULA_SINKS[sink_type]
    except KeyError:
        raise NotImplementedError() from None

    writer(exclusion_filename, formatted_excluded_formulas)
    return None


def write_excluded_formulas(output, *args):
    """Write excluded formulas using either the legacy or the output-object API.

    Legacy signature:
        write_excluded_formulas(sink_type, exclusion_filename, formulas)

    Preferred signature:
        write_excluded_formulas(output, formatter, excluded_formulas_heading=None)
    """
    if isinstance(output, SinkType):
        if len(args) != 2:
            raise TypeError('legacy write_excluded_formulas expects 3 arguments')
        return _write_excluded_formulas_legacy(output, args[0], args[1])

    if not isinstance(output, ExcludedFormulaOutput):
        raise TypeError('ExcludedFormulaOutput instance expected')

    if len(args) not in {1, 2}:
        raise TypeError(
            'write_excluded_formulas expects output, formatter, '
            '[excluded_formulas_heading]'
        )

    formatter = args[0]
    excluded_formulas_heading = args[1] if len(args) == 2 else None
    if not formatter.get_excluded():
        return None
    output.write_excluded_formulas(formatter, excluded_formulas_heading)
    return None
