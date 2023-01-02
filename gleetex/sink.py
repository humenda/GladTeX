"""
Sink functionality for outputs.


GladTeX is capable of writing to different output formats, called a sink. A sink
may parse the source and process the formulas in the document, replacing it with
its converted equivalent. Tis decouples the GleeTeX-internal logic from HTML and
allows using it e.g. as a filter for Pandoc (JSON-encoded).
"""

import enum
import html

EXCLUSION_FILE_NAME = 'excluded-descriptions.html'

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
    json_file = 2
    inline = 3

def html_write_excluded_file(exclusion_filename, formatted_excluded_formulas):
    """Write back list of excluded formulas.
    Formulas that are too long or too complex for the alt tag are excluded to a
    separate file. This function initiates the writing process to the external
    file."""
    with open(exclusion_filename, 'w', encoding='UTF-8') as file:
        file.write(HTML_TEMPLATE_HEAD)
        _html_write_excluded(file, formatted_excluded_formulas)
        file.write('\n</body>\n</html>\n')


def html_write_excluded_body(exclusion_filename, formatted_excluded_formulas):
    with open(exclusion_filename, 'w', encoding='UTF-8') as file:
        _html_write_excluded(file, formatted_excluded_formulas)


def _html_write_excluded(file_obj, formatted_excluded_formulas):
    for label, formula in formatted_excluded_formulas.items():
        escaped_formula = html.escape(formula)
        file_obj.write(f'<a id="{label}"><pre>{escaped_formula}</pre></a>\n')


# Map the sink type to their processing function.
EXCLUSION_FORMULA_SINKS = {
    SinkType.html_file: html_write_excluded_file,
    SinkType.html_body: html_write_excluded_body,
}
