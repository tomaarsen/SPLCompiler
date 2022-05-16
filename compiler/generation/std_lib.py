from compiler.generation.instruction import Instruction
from compiler.generation.line import Line

STD_LIB_LIST = {
    # # # # # # # # # # # # # #
    # Checks if list is empty
    "_is_empty": [
        Line(label="_is_empty"),
        Line(Instruction.LINK, 0),
        # Get reference
        Line(Instruction.LDL, -2),
        # Get length
        Line(Instruction.LDA, -1),
        # Compre with 0
        Line(Instruction.LDC, 0),
        Line(Instruction.EQ),
        # Clean-up
        Line(Instruction.STR, "RR"),
        Line(Instruction.UNLINK),
        Line(Instruction.RET),
    ],
    # # # # # # # # # # # # # #
    # Creates a reference to an empty list of length 0.
    "_get_empty_list": [
        Line(Instruction.LDC, 0),  # Length
        Line(Instruction.LDC, 0xBABE),  # Pointer
        Line(Instruction.STMH, 2),  # Put on stack
    ],
    # # # # # # # # # # # # # #
    # var b = 1 : a;
    # 1. Create a new reference b
    # 2. Copy the contents of a to b
    # 3. Prepend the element to a;
    "_get_new_list_pointer_and_copy_contents": [
        Line(label="_get_new_list_pointer_and_copy_contents"),
        Line(Instruction.LINK, 0),
        # Top of stack in subroutine is:
        # Length remaining
        # Current pointer to copy from
        # Create a stack as described above:
        # Load reference to copy from
        Line(Instruction.LDL, -2),
        # Load length
        Line(Instruction.LDH, -1),
        # Copy the length, for later use
        Line(Instruction.LDL, 1),
        # Check if length == 0
        Line(Instruction.LDC, 0),
        Line(Instruction.EQ),
        # Jump to end of loop if local length == 0
        Line(Instruction.BRT, "_return_new_list"),
        # Set current reference to copy from
        Line(Instruction.LDL, -2),
        # Update reference to first element
        # Get reference
        Line(Instruction.LDL, 2),
        # Get new reference
        Line(Instruction.LDA, 0),
        # Update reference
        Line(Instruction.STL, 2),
        Line(label="_load_loop"),
        # Recursively load all elements of list
        # Get reference
        Line(Instruction.LDL, 2),
        # Get element
        Line(Instruction.LDA, -1),
        # Update reference
        Line(Instruction.LDL, 2),
        Line(Instruction.LDA, 0),
        Line(Instruction.STL, 2),
        # Decrement length of remaining element
        # Get length
        Line(Instruction.LDL, 1),
        # Decrement by 1
        Line(Instruction.LDC, 1),
        Line(Instruction.SUB),
        # Store it
        Line(Instruction.STL, 1),
        # Check if need to continue the loop
        # Get length
        Line(Instruction.LDL, 1),
        # Length == 0?
        Line(Instruction.LDC, 0),
        Line(Instruction.EQ),
        # Continue loop
        Line(Instruction.BRT, "_load_loop"),
        # At this point all elements of the original list are in order on the stack
        # Reset the local length
        # Load reference to copy from
        Line(Instruction.LDL, -2),
        # Load length
        Line(Instruction.LDH, -1),
        # Store the length, for later use
        Line(Instruction.STL, 1),
        # Create empty reference
        Line(Instruction.LDC, 0),  # Length
        Line(Instruction.LDC, 47806),  # Pointer
        Line(Instruction.STMH, 2),  # Put on stack
        # Store in RR
        Line(Instruction.STR, "RR"),
        Line(Instruction.LDR, "RR"),
        Line(label="_store_loop"),
        # Recursively store all elements of list, by prepending
        Line(Instruction.BSR, "_prepend_element"),
        # Remove prepended element from stack
        Line(Instruction.SWP),
        Line(Instruction.AJS, -1),
        # Decrement length of remaining element
        # Get length
        Line(Instruction.LDL, 1),
        # Decrement by 1
        Line(Instruction.LDC, 1),
        Line(Instruction.SUB),
        # Store it
        Line(Instruction.STL, 1),
        # Check if need to continue the loop
        # Get length
        Line(Instruction.LDL, 1),
        # Length == 0?
        Line(Instruction.LDC, 0),
        Line(Instruction.EQ),
        # Continue loop
        Line(Instruction.BRF, "_store_loop"),
        # End the loop, and return the reference to the new list
        Line(label="_return_new_list"),
        # Clean-up
        Line(Instruction.UNLINK),
        # Replace the pointer with a new pointer
        Line(Instruction.RET),
    ],
    # # # # # # # # # # # # # #
    # Prepends element x to a list.
    # Assumes stack layout:
    # 	x
    # 	reference to list
    "_prepend_element": [
        # Step 0: Create label
        Line(label="_prepend_element"),
        # Step 1: Increment length by 1
        # Copy the pointer to (length, next*)
        Line(Instruction.LINK, 0),
        Line(Instruction.LDL, -2),
        # Load current length
        Line(Instruction.LDA, -1),
        # Add one to current length
        Line(Instruction.LDC, 1),
        Line(Instruction.ADD),
        # Get the reference to (length, next*)
        Line(Instruction.LDL, -2),
        # Push the new length to the Heap
        Line(Instruction.STA, -1),
        # Step 2: Check if the updated length is > 1
        # Get the reference to (length, next*)
        Line(Instruction.LDL, -2),
        # Load current length
        Line(Instruction.LDA, -1),
        # Compare current length > 1
        Line(Instruction.LDC, 1),
        Line(Instruction.GT),
        # Jump to step 3b, if applicable
        Line(Instruction.BRT, "_prepend_list_non_empty_start"),
        # Step 3a: If list is currently empty (length <= 1), make next* point to our new value
        # Load the value to be prepended
        Line(Instruction.LDL, -3),
        # Load pointer
        Line(Instruction.LDC, 47806),
        # Store (value, pointer) on heap
        Line(Instruction.STMH, 2),
        # Get the reference to (length, next*)
        Line(Instruction.LDL, -2),
        # Update the pointer of (length, next*) to point to the prepended element
        Line(Instruction.STA, 0),
        # Jump over step 3b
        Line(Instruction.BRA, "_prepend_list_non_empty_end"),
        # Step 3b: If list is currently non-empty (length > 1)
        Line(label="_prepend_list_non_empty_start"),
        # Get the value to be prepended
        Line(Instruction.LDL, -3),
        # Get the reference to (length, next*)
        Line(Instruction.LDL, -2),
        # Load the pointer of the second element
        Line(Instruction.LDA, 0),
        # Store (value, pointer) on heap
        Line(Instruction.STMH, 2),
        # Get the reference to (length, next*)
        Line(Instruction.LDL, -2),
        # Update (length, next*) to point to the new (value, point)
        Line(Instruction.STA, 0),
        # Clean-up
        Line(label="_prepend_list_non_empty_end"),
        # Line(Instruction.STR, "RR"),
        Line(Instruction.UNLINK),
        # Replace the pointer with a new pointer
        Line(Instruction.RET),
    ],
    "_tail": [
        # Check if length <= 1, if so we return the empty list
        Line(label="_tail"),
        # Create space to perform computations
        Line(Instruction.LINK, 0),
        # Yield first element
        Line(Instruction.LDL, -2),
        # Yield length
        Line(Instruction.LDA, -1),
        # Check if length <= 1
        Line(Instruction.LDC, 1),
        Line(Instruction.LE),
        Line(Instruction.BRF, "_tail_rest_of_list"),
        # Yield empty list
        Line(Instruction.LDC, 0),  # Length
        Line(Instruction.LDC, 47806),  # Pointer
        Line(Instruction.STMH, 2),  # Put on stack
        # Store value in RR
        Line(Instruction.STR, "RR"),
        # Clean-up
        Line(Instruction.UNLINK),
        Line(Instruction.RET),
        # Else yield pointer to remaining list
        Line(label="_tail_rest_of_list"),
        # Yield length
        Line(Instruction.LDL, -2),
        Line(Instruction.LDA, -1),
        # Subtract 1
        Line(Instruction.LDC, 1),
        Line(Instruction.SUB),
        # Yield pointer to tail
        Line(Instruction.LDL, -2),
        Line(Instruction.LDA, 0),
        Line(Instruction.LDA, 0),
        # Put length, next* on stack
        Line(Instruction.STMH, 2),
        # Store value in RR
        Line(Instruction.STR, "RR"),
        # Clean-up
        Line(Instruction.UNLINK),
        Line(Instruction.RET),
    ],
    "_head": [
        Line(label="_head"),
        # Create space to perform computations
        Line(Instruction.LINK, 0),
        # Get reference
        Line(Instruction.LDL, -2),
        # Get length
        Line(Instruction.LDA, -1),
        # Check if length == 0
        Line(Instruction.LDC, 0),
        Line(Instruction.EQ),
        Line(Instruction.BRF, "_head_first"),
        # If length == 0 -> return -1
        Line(Instruction.LDC, -1),
        # Store in RR
        Line(Instruction.STR, "RR"),
        # Clean-up
        Line(Instruction.UNLINK),
        # Yield empty list
        Line(Instruction.LDC, 0),  # Length
        Line(Instruction.LDC, 47806),  # Pointer
        Line(Instruction.STMH, 2),  # Put on stack
        # Return the first element
        Line(label="_head_first"),
        # Get reference to (length, first*)
        Line(Instruction.LDL, -2),
        # Get next*
        Line(Instruction.LDA, 0),
        # Yield value
        Line(Instruction.LDA, -1),
        # Store in RR
        Line(Instruction.STR, "RR"),
        # Clean-up
        Line(Instruction.UNLINK),
        Line(Instruction.RET),
    ],
}
