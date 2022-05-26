from tests.generation.util import execute


def test_field_expr():
    program = r"""
    main(){
        var b = [1..5] : [6..10] : [11..15] : [];
        println(b);
        println(b[1]);
        println(b.tl[1].hd);
        println(b.tl[0][3]);
    }
    """
    expected = """\
[[1, 2, 3, 4, 5], [6, 7, 8, 9, 10], [11, 12, 13, 14, 15]]
[6, 7, 8, 9, 10]
11
9
"""
    output = execute(program)
    assert output.splitlines() == expected.splitlines()


def test_field_index_assign():
    program = r"""
    main(){
        var b = [1..5] : [6..10] : [11..15] : [];
        b[0][2] = 8;
        b[1][0] = 12;
        b[2][4] = 24;
        print(b);
    }
    """
    expected = "[[1, 2, 8, 4, 5], [12, 7, 8, 9, 10], [11, 12, 13, 14, 24]]"
    output = execute(program)
    assert output.splitlines() == expected.splitlines()


def test_field_head_assign():
    program = r"""
    main(){
        var b = [1..5] : [6..10] : [11..15] : [];
        b.hd = 2 : [];
        b[2].hd = 3;
        print(b);
    }
    """
    expected = "[[2], [6, 7, 8, 9, 10], [3, 12, 13, 14, 15]]"
    output = execute(program)
    assert output.splitlines() == expected.splitlines()


def test_if_else():
    program = """
    cond_print(x){
        var a = 12;
        if (x < a){
            if (x > 5){
                print(x);
                print(" is larger than 5, but smaller than ");
                println(a);
            }
            else{
                print(x);
                print(" is smaller or equal to 5, and smaller than ");
                println(a);
            }
        }
        else{
            print(x);
            print(" is greater or equal to ");
            println(a);
        }
    }

    main(){
        cond_print(12);
        cond_print(10);
        cond_print(4);
        cond_print(24);
    }
    """
    expected = """\
12 is greater or equal to 12
10 is larger than 5, but smaller than 12
4 is smaller or equal to 5, and smaller than 12
24 is greater or equal to 12"""
    output = execute(program)
    assert output.splitlines() == expected.splitlines()


def test_continue():
    program = r"""
    main(){
        int x = 13;

        for i in [1..5]{
            if (i <= 2){
                println("< 2");
                continue;
            }
            println(i);
        }

        print('\n');

        while (x > 7){
            x = x - 1;
            if (x > 10){
                println("> 10");
                continue;
            }
            println(x);
        }
    }"""
    expected = "< 2\n< 2\n3\n4\n5\n\n> 10\n> 10\n10\n9\n8\n7\n"
    output = execute(program)
    assert output.splitlines() == expected.splitlines()


def test_break():
    program = r"""
    main(){
        int x = 13;

        for i in [1..5]{
            if (i > 3){
                println("> 3");
                break;
            }
            println(i);
        }

        print('\n');

        while (x > 7){
            x = x - 1;
            if (x < 10){
                println("< 10");
                break;
            }
            println(x);
        }
    }"""
    expected = "1\n2\n3\n> 3\n\n12\n11\n10\n< 10\n"
    output = execute(program)
    assert output.splitlines() == expected.splitlines()
