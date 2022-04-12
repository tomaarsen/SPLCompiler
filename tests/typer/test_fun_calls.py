from pprint import pprint

from tests.typer.util import type_tree

from compiler.tree.tree import (  # isort:skip
    CharTypeNode,
    FunDeclNode,
    FunTypeNode,
    IntTypeNode,
    Node,
    PolymorphicTypeNode,
    SPLNode,
    VarDeclNode,
)


def test_defined_1():
    """
    Expected:

    id(n) :: a -> a {
        return n;
    }

    foo(a) :: b -> b {
        return id(a);
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/defined_1.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_one],
                        ret_type=PolymorphicTypeNode() as poly_two,
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_three],
                        ret_type=PolymorphicTypeNode() as poly_four,
                    )
                ),
            ]
        ):
            assert poly_one == poly_two
            assert poly_three == poly_four
            assert poly_one != poly_three

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_defined_2():
    """
    Expected:

    id(n) :: a -> a {
        return n;
    }

    foo(a) :: b -> Int {
        return id(12);
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/defined_2.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_one],
                        ret_type=PolymorphicTypeNode() as poly_two,
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_three],
                        ret_type=IntTypeNode(),
                    )
                ),
            ]
        ):
            assert poly_one == poly_two
            assert poly_one != poly_three

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_defined_3():
    """
    Expected:

    id(n) :: a -> a {
        return n;
    }

    foo(a) :: Int -> Int {
        a = 12;
        return id(a);
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/defined_3.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_one],
                        ret_type=PolymorphicTypeNode() as poly_two,
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[IntTypeNode()],
                        ret_type=IntTypeNode(),
                    )
                ),
            ]
        ):
            assert poly_one == poly_two

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_defined_4():
    """
    Expected:

    id(n) :: a -> a {
        return n;
    }

    foo(a) :: Int -> Int {
        return id(a) + 12;
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/defined_4.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_one],
                        ret_type=PolymorphicTypeNode() as poly_two,
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[IntTypeNode()],
                        ret_type=IntTypeNode(),
                    )
                ),
            ]
        ):
            assert poly_one == poly_two

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_defined_5():
    """
    Expected:

    id(n) :: a -> a {
        return n;
    }

    foo(a) :: Int -> Int {
        return id(a - 12);
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/defined_5.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_one],
                        ret_type=PolymorphicTypeNode() as poly_two,
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[IntTypeNode()],
                        ret_type=IntTypeNode(),
                    )
                ),
            ]
        ):
            assert poly_one == poly_two

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_defined_6():
    """
    Expected:

    double(n) :: Int -> Int {
        return n + n;
    }

    foo(a) :: Int -> Int {
        return double(a);
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/defined_6.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[IntTypeNode()],
                        ret_type=IntTypeNode(),
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[IntTypeNode()],
                        ret_type=IntTypeNode(),
                    )
                ),
            ]
        ):
            pass

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_defined_7():
    """
    Expected:

    id(n) :: a -> a {
        return n;
    }

    main() -> Char {
        var b = id('a');
        return b;
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/defined_7.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_one],
                        ret_type=PolymorphicTypeNode() as poly_two,
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[],
                        ret_type=CharTypeNode(),
                    )
                ),
            ]
        ):
            assert poly_one == poly_two

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_undefined_1():
    """
    Expected:

    foo(a) :: a -> a {
        return id(a);
    }

    id(n) :: b -> b {
        return n;
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/undefined_1.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_one],
                        ret_type=PolymorphicTypeNode() as poly_two,
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_three],
                        ret_type=PolymorphicTypeNode() as poly_four,
                    )
                ),
            ]
        ):
            assert poly_one == poly_two
            assert poly_three == poly_four
            assert poly_one != poly_three

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_undefined_2():
    """
    Expected:

    foo(a) :: a -> Int {
        return id(12);
    }

    id(n) :: b -> b {
        return n;
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/undefined_2.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_three],
                        ret_type=IntTypeNode(),
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_one],
                        ret_type=PolymorphicTypeNode() as poly_two,
                    )
                ),
            ]
        ):
            assert poly_one == poly_two
            assert poly_one != poly_three

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_undefined_3():
    """
    Expected:

    foo(a) :: Int -> Int {
        a = 12;
        return id(a);
    }

    id(n) :: a -> a {
        return n;
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/undefined_3.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[IntTypeNode()],
                        ret_type=IntTypeNode(),
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_one],
                        ret_type=PolymorphicTypeNode() as poly_two,
                    )
                ),
            ]
        ):
            assert poly_one == poly_two

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_undefined_4():
    """
    Expected:

    foo(a) {
        return id(a) + 12;
    }

    id(n){
        return n;
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/undefined_4.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[IntTypeNode()],
                        ret_type=IntTypeNode(),
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_one],
                        ret_type=PolymorphicTypeNode() as poly_two,
                    )
                ),
            ]
        ):
            assert poly_one == poly_two

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_undefined_5():
    """
    Expected:

    foo(a) :: Int -> Int {
        return id(a - 12);
    }

    id(n) :: a -> a {
        return n;
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/undefined_5.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[IntTypeNode()],
                        ret_type=IntTypeNode(),
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_one],
                        ret_type=PolymorphicTypeNode() as poly_two,
                    )
                ),
            ]
        ):
            assert poly_one == poly_two

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_undefined_6():
    """
    Expected:

    foo(a) :: Int -> Int {
        return double(a);
    }

    double(n) :: Int -> Int {
        return n + n;
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/undefined_6.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[IntTypeNode()],
                        ret_type=IntTypeNode(),
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[IntTypeNode()],
                        ret_type=IntTypeNode(),
                    )
                ),
            ]
        ):
            pass

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_undefined_7():
    """
    Expected:

    main(){
        var b = id('a');
        return b;
    }

    id(n) :: b -> b {
        return n;
    }
    """
    tree = type_tree("data/custom/typerError/fun_calls/undefined_7.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[],
                        ret_type=CharTypeNode(),
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[PolymorphicTypeNode() as poly_one],
                        ret_type=PolymorphicTypeNode() as poly_two,
                    )
                ),
            ]
        ):
            assert poly_one == poly_two

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")
