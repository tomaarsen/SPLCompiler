import sys

from compiler.util import Colors, Span


# Class used to create messages, which can be communicated to the programmer
class Communicator:

    # Creates an appropriate message string from the given arguments
    @staticmethod
    def create_message(
        program: str,
        span: Span,
        class_name="CompilerError",
        before: str = "",
        after: str = "",
        n_before: int = 1,
        n_after: int = 1,
        color=Colors.RED,
    ) -> str:
        lines = program.splitlines()
        error_lines = lines[
            max(0, span.start_ln - n_before - 1) : span.end_ln + n_after
        ]
        final_error_lines = []
        start_line_no = max(1, span.start_ln - n_before)
        end_line_no = start_line_no + len(error_lines) - 1
        for i, line in enumerate(error_lines, start=start_line_no):
            # Determine the number of spaces between e.g. '8.' and the code.
            # See the * in the following example:
            #    *8. var a = 12;
            # -> *9. var b = 15;
            #    10. fun(c, d) {
            padding = " " * (len(str(end_line_no)) - len(str(i)))
            final_line = ""
            # If this line contains denotated spans:
            if i >= span.start_ln and i <= span.end_ln:
                # First line
                if i == span.start_ln:
                    # Do not color outside of span on first line
                    final_line += f"-> {padding}{i}. {line[:span.start_col]}"

                    # If we have more than 1 line, color the remaining line
                    if span.multiline:
                        final_line += f"{color}{line[span.start_col:]}{Colors.ENDC}"
                    # If there is one line, color up until the correct col
                    else:
                        final_line += (
                            f"{color}{line[span.start_col:span.end_col]}{Colors.ENDC}"
                        )
                        final_line += line[span.end_col :]

                # Color lines (if any) that are in between the first and last line
                elif i > span.start_ln and i < span.end_ln:
                    final_line += f"-> {padding}{i}. {color}{line}{Colors.ENDC}"
                # The last line, of a multiline
                else:
                    final_line += (
                        f"-> {padding}{i}. {color}{line[:span.end_col]}{Colors.ENDC}"
                    )
                    final_line += line[span.end_col :]

            else:
                final_line += f"   {padding}{i}. {line}"
            final_error_lines.append(final_line)

        message = (
            class_name
            # __class__.__name__
            + ": "
            + before
            + "\n"
            + "\n".join(final_error_lines)
        )
        if after:
            message += "\n" + after
        return message

    # Communicates all warnings and errors to the programmer
    # In case of any errors, the compiler will stop with an exception
    @staticmethod
    def communicate(stage_of_exception) -> None:
        ErrorRaiser.__combine_errors__()

        warnings = "".join(
            [str(warning) + "\n\n" for warning in WarningRaiser.WARNINGS[:10]]
        )
        if warnings:
            if len(WarningRaiser.WARNINGS) > 10:
                omitting_multiple_warnings = len(WarningRaiser.WARNINGS) - 10 > 1
                warnings += f"Showing 10 warnings, omitting {len(WarningRaiser.WARNINGS)-10} warning{'s' if omitting_multiple_warnings else ''}..."
            WarningRaiser.WARNINGS.clear()
            print("\n", warnings)

        errors = "".join(["\n\n" + str(error) for error in ErrorRaiser.ERRORS[:10]])
        if errors:
            sys.tracebacklimit = -1
            if len(ErrorRaiser.ERRORS) > 10:
                omitting_multiple_errors = len(ErrorRaiser.ERRORS) - 10 > 1
                errors += f"\n\nShowing 10 errors, omitting {len(ErrorRaiser.ERRORS)-10} error{'s' if omitting_multiple_errors else ''}..."
            ErrorRaiser.ERRORS.clear()
            raise stage_of_exception(errors)


# Used to store all the accumulated warnings
class WarningRaiser:
    WARNINGS = []


# Used to store all the accumulated errors and combine UnexpectedCharacterError
class ErrorRaiser:
    ERRORS = []

    @staticmethod
    def __combine_errors__() -> None:
        from compiler.error.error import CompilerError
        from compiler.error.scanner_error import UnexpectedCharacterError

        # Check if we have any consecutive UnexpectedCharacterError
        # First sort on line_no, and then on start of the error in the line
        # If error object has no span attribute, then sort it on top
        ErrorRaiser.ERRORS.sort(
            key=lambda error: (error.span.start_ln, error.span.start_col)
            if isinstance(error, CompilerError)
            else (0, 0)
        )

        length = len(ErrorRaiser.ERRORS)
        i = 0
        while i < length - 1:
            # Ensure that consecutive objects are the (1) same error, (2) have same line_no and (3) are next to eachothers
            current_error = ErrorRaiser.ERRORS[i]
            next_error = ErrorRaiser.ERRORS[i + 1]
            if (
                isinstance(current_error, UnexpectedCharacterError)
                and isinstance(next_error, UnexpectedCharacterError)
                and current_error.span.start_ln == next_error.span.start_ln
                and current_error.span.end_col == next_error.span.start_col
            ):

                # Reuse current_error to prevent additional call to __post_init__ on object creation
                next_error.span = Span(
                    line_no=(current_error.span.start_ln, current_error.span.end_ln),
                    span=(current_error.span.start_col, next_error.span.end_col),
                )
                del ErrorRaiser.ERRORS[i]
                length -= 1
            else:
                i += 1
