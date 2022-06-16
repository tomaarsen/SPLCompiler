import pytest

from tests.generation.util import execute, execute_file

programs = [
    ### VarDeclNode
    (
        """
var A = True;
var B = 12;
var C = 'a';
var D = "hello";

main(){
    println(A);
    println(B);
    println(C);
    println(D);
}
""",
        "True\n12\na\nhello\n",
    ),
    (
        """
main(){
    println(A);
    println(B);
    println(C);
    println(D);
}

var A = True;
var B = 12;
var C = 'a';
var D = "hello";
""",
        "True\n12\na\nhello\n",
    ),
    (
        """
main(){
    A = False;
    B = 24;
    C = 'd';
    D = "there";
    println(A);
    println(B);
    println(C);
    println(D);
}

var A = True;
var B = 12;
var C = 'a';
var D = "hello";
""",
        "False\n24\nd\nthere\n",
    ),
    ### Fields
    (
        """
main(){
    var a = (1, 2) : (3, 4): [];
    println(a);

    println(a.hd);
    println(a.tl);

    println(a.hd.fst);
    println(a.hd.snd);

    println(a.tl.hd);
    println(a.tl.tl);

    println(a.tl.hd.fst);
    println(a.tl.hd.snd);

    println(a[0].fst);
    println(a[0].snd);

    println(a[1].fst);
    println(a[1].snd);
}
""",
        """[(1, 2), (3, 4)]
(1, 2)
[(3, 4)]
1
2
(3, 4)
[]
3
4
1
2
3
4
""",
    ),
    (
        """
main(){
    var a = ("hello", "there");
    println(a);

    println(a.fst);
    println(a.snd);

    println(a.fst.hd);
    println(a.fst.tl);
    println(a.fst.tl.tl.tl.tl);

    println(a.snd.hd);
    println(a.snd.tl);
    println(a.snd.tl.tl.tl.tl);

    println(a.fst[3]);
    println(a.snd[3]);
}
""",
        """(hello, there)
hello
there
h
ello
o
t
here
e
l
r
""",
    ),
    (
        """
main(){
    var a = (1, 2) : (3, 4): [];
    a.hd = (5, 6);
    println(a);
    a.hd.fst = 7;
    println(a);
    a.hd.snd = 8;
    println(a);
    a[1].fst = 9;
    println(a);
    a[1].snd = 10;
    println(a);
    a[0] = (11, 12);
    println(a);
    a.tl = (13, 14) : [];
    println(a);
    a.tl = (15, 16) : (17, 18) : [];
    println(a);
    a.tl = [];
    println(a);
    a.tl = (-1, 20) : [];
    a.tl.hd.fst = 19;
    println(a);
    a.tl[0].snd = 21;
    println(a);
}
""",
        """[(5, 6), (3, 4)]
[(7, 6), (3, 4)]
[(7, 8), (3, 4)]
[(7, 8), (9, 4)]
[(7, 8), (9, 10)]
[(11, 12), (9, 10)]
[(11, 12), (13, 14)]
[(11, 12), (15, 16), (17, 18)]
[(11, 12)]
[(11, 12), (19, 20)]
[(11, 12), (19, 21)]
""",
    ),
    (
        """
main(){
    var a = ("hello", "there");
    a.fst = "good morning";
    println(a);
    a.snd = "friend";
    println(a);
    a.fst = 'b' : 'a' : a.fst.tl.tl.tl;
    println(a);
    a.fst[5] = 'e';
    println(a);
    // This is broken:
    //a.fst.tl.tl.tl = " afternoon";
    //println(a);
    // (bad afternoon, friend)
}
""",
        """(good morning, there)
(good morning, friend)
(bad morning, friend)
(bad merning, friend)
""",
    ),
]


@pytest.mark.parametrize("program, expected", programs)
def test_program(program: str, expected: str):
    predicted = execute(program)
    assert predicted == expected
