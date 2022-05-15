from compiler.generation.instruction import Instruction
from compiler.generation.line import Line

STD_LIB = """
_print_Bool:
	link 0
    ldl -2
	brt _print_Bool_Then

_print_Bool_Else:
	ldc 70			; 'F'
	trap 1			; print('F')
	ldc 97			; 'a'
	trap 1			; print('a')
	ldc 108			; 'l'
	trap 1			; print('l')
	ldc 115			; 's'
	trap 1			; print('s')
	ldc 101			; 'e'
	trap 1			; print('e')
	bra _print_Bool_End

_print_Bool_Then:
	ldc 84			; 'T'
	trap 1			; print('T')
	ldc 114			; 'r'
	trap 1			; print('r')
	ldc 117			; 'u'
	trap 1			; print('u')
	ldc 101			; 'e'
	trap 1			; print('e')

_print_Bool_End:
	unlink
	ret			; return;
"""

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
        Line(Instruction.LDC, 47806),  # Pointer
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
    "_print_list_int": [
        Line(label="_print_list_int"),
        Line(Instruction.LINK, 0),
        # Step 0: Print "["
        Line(Instruction.LDC, 91, comment="Load '['"),
        Line(Instruction.TRAP, 1, comment="Print '['"),
        # Step 1: check if length = 0
        # Load reference to list
        Line(Instruction.LDL, -2),
        # Load length of list
        Line(Instruction.LDH, -1),
        # Copy the length, for later use
        Line(Instruction.LDL, 1),
        # Check if length == 0
        Line(Instruction.LDC, 0),
        Line(Instruction.EQ),
        # Step 2: Loop over all elements
        # Jump to end of loop if length == 0
        Line(Instruction.BRT, "_print_end_of_list"),
        # Step 2a: prepare loop
        # Load reference to list
        Line(Instruction.LDL, -2),
        # Load next*
        Line(Instruction.LDH, 0),
        # Start of loop component
        Line(label="_print_loop"),
        # Step 2b: Keep track of current pointer
        Line(Instruction.LDL, 2),
        # Step 2c: Print single element
        # Load next value
        Line(Instruction.LDH, -1),
        # Print it
        Line(Instruction.TRAP, 0),
        # Step 2d: Update length
        # Load localally stored length
        Line(Instruction.LDL, 1),
        # Subtract 1
        Line(Instruction.LDC, 1),
        Line(Instruction.SUB, 1),
        # Write to local copy
        Line(Instruction.STL, 1),
        # Step 2d: Print comma if needed
        # Load locally stored length
        Line(Instruction.LDL, 1),
        # Check if remaining elements / local length == 0
        Line(Instruction.LDC, 0),
        Line(Instruction.EQ),
        # Escape loop if true
        Line(Instruction.BRT, "_print_end_of_list"),
        # Else print comma
        Line(Instruction.LDC, 44, comment="Load ','"),
        Line(Instruction.TRAP, 1, comment="Print ','"),
        # Print " "
        Line(Instruction.LDC, 32, comment="Load ' '"),
        Line(Instruction.TRAP, 1, comment="Print ' '"),
        # Step 2e: Update pointer and continue loop
        # Get pointer
        Line(Instruction.LDL, 2),
        # Load new pointer
        Line(Instruction.LDA, 0),
        # Update locally stored pointer
        Line(Instruction.STL, 2),
        # Continue loop
        Line(Instruction.BRA, "_print_loop"),
        # Step 3: print "]"
        Line(label="_print_end_of_list"),
        Line(Instruction.LDC, 93, comment="Load ']'"),
        Line(Instruction.TRAP, 1, comment="Print ']'"),
        # Clean-up
        Line(Instruction.UNLINK),
        # Replace the pointer with a new pointer
        Line(Instruction.RET),
    ],
    # Todo: generalize to n nested listed, instead of singly nested list
    "_print_nested_list_int": [
        # Stack contains a pointer to a nested list
        Line(label="_print_nested_list_int"),
        # Move MP
        Line(Instruction.LINK, 0),
        Line(Instruction.LDC, 91, comment="Load '['"),
        Line(Instruction.TRAP, 1, comment="Print '['"),
        # Stack:
        # Pointer
        # Length
        # Get pointer
        Line(Instruction.LDL, -2),
        # Copy pointer
        Line(Instruction.LDL, -2),
        # Get length
        Line(Instruction.LDA, -1),
        Line(label="_start_print_nested_int_loop"),
        # Copy length
        Line(Instruction.LDL, 1),
        # Check if length == 0
        Line(Instruction.LDC, 0),
        Line(Instruction.EQ),
        # Exit loop if true
        Line(Instruction.BRT, "end_print_nested_int"),
        # Set local pointer to first element
        Line(Instruction.LDL, -2),
        Line(Instruction.LDA, 0),
        Line(Instruction.STL, 1),
        # Load pointer to be printed
        Line(Instruction.LDL, 1),
        # Load beginning of next list item
        Line(Instruction.LDL, 1),
        Line(label="Test"),
        Line(Instruction.LDA, -1),
        # Print int list
        Line(Instruction.BSR, "_print_list_int"),
        Line(Instruction.SWP),
        Line(Instruction.AJS, -1),
        # Decrement local length
        Line(Instruction.LDL, 2),
        Line(Instruction.LDC, 1),
        Line(Instruction.SUB),
        Line(Instruction.STL, 2),
        # Load next pointer
        Line(Instruction.LDL, 1),
        Line(Instruction.LDA, 0),
        # Check if there is another element:
        Line(Instruction.LDL, 2),
        Line(Instruction.LDC, 0),
        # Length == ?
        Line(Instruction.EQ),
        Line(Instruction.BRT, "end_print_nested_int"),
        # Print ","
        Line(Instruction.LDC, 44, comment="Load ','"),
        Line(Instruction.TRAP, 1, comment="Print ','"),
        Line(Instruction.BRA, "Test"),
        Line(label="end_print_nested_int"),
        Line(Instruction.LDC, 93, comment="Load ']'"),
        Line(Instruction.TRAP, 1, comment="Print ']'"),
        # Clean-up
        Line(Instruction.UNLINK),
        Line(Instruction.RET),
    ],
}