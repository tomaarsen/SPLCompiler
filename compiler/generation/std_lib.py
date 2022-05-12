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
