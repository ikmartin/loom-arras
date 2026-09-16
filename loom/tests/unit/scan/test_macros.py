from loom.scan.macros import expand, is_math_macro, parse_macros, to_mathjax


def test_macros_all_forms() -> None:
    text = r"""
\newcommand{\Res}{\mathrm{Res}}
\newcommand\GW{Gromov--Witten}
\renewcommand{\red}[1]{\textcolor{red}{#1}}
\providecommand{\pair}[2][x]{(#1,#2)}
\def\foo#1#2{[#1|#2]}
\DeclareMathOperator{\Spec}{Spec}
\DeclareMathOperator*{\colim}{colim}
\let\Hom\operatorname
\NewDocumentCommand\here{m o}{HERE #1}
\newcommand{\multi}{first
line and second}
"""
    m = parse_macros(text)
    assert m["Res"].body == r"\mathrm{Res}" and m["Res"].args == 0
    assert m["GW"].body == "Gromov--Witten"
    assert m["red"].args == 1 and expand(m["red"], ["hi"]) == r"\textcolor{red}{hi}"
    assert m["pair"].args == 2 and m["pair"].default == "x"
    assert expand(m["pair"], ["a", "b"]) == "(a,b)" and expand(m["pair"], ["", "b"]) == "(,b)"
    assert m["foo"].args == 2 and expand(m["foo"], ["1", "2"]) == "[1|2]"
    assert m["Spec"].body == r"\operatorname{Spec}" and m["colim"].body == r"\operatorname*{colim}"
    assert m["Hom"].kind == "let"
    assert m["here"].args == 2
    assert "second" in m["multi"].body


def test_macros_math_classification_and_mathjax() -> None:
    m = parse_macros(r"\newcommand{\Res}{\mathrm{Res}} \newcommand{\GW}{Gromov--Witten}")
    assert is_math_macro(m["Res"]) and not is_math_macro(m["GW"])
    assert to_mathjax(m) == [
        {"name": "GW", "args": 0, "body": "Gromov--Witten"},
        {"name": "Res", "args": 0, "body": r"\mathrm{Res}"},
    ]


def test_macros_later_definition_wins() -> None:
    m = parse_macros(r"\newcommand{\a}{1} \renewcommand{\a}{2}")
    assert m["a"].body == "2"
