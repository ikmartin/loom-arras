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


def test_conditionals_a_math_renderer_cannot_evaluate_are_resolved() -> None:
    """MathJax implements no TeX conditionals, so `\\arr` reached the page as the words `\\ifinner`, `\\else` and `\\fi` in error red beside two arrows (seen on the ACGS import). `\\ifinner` asks exactly what `\\mathchoice` selects on; `\\ifmmode` is always true inside math."""
    m = parse_macros(r"\newcommand\arr{\ifinner\to\else\longrightarrow\fi}")
    assert to_mathjax(m) == [{"name": "arr", "args": 0, "body": r"\mathchoice{\longrightarrow}{\to}{\to}{\to}"}]

    m = parse_macros(r"\newcommand\x{\ifmmode A\else B\fi}")
    assert to_mathjax(m)[0]["body"] == "A"

    m = parse_macros(r"\newcommand\y{a\ifinner\to\fi b}")
    assert to_mathjax(m)[0]["body"] == r"a\mathchoice{}{\to}{\to}{\to} b"  # the space after \fi is the author's


def test_a_conditional_that_cannot_be_resolved_is_left_alone() -> None:
    """Guessing a branch of a test the renderer might handle differently would silently change the mathematics."""
    body = r"\ifdim 1pt>0pt A\else B\fi"
    m = parse_macros(r"\newcommand\z{" + body + "}")
    assert to_mathjax(m)[0]["body"] == body


def test_declared_alphabets_become_the_nearest_alphabet_a_renderer_has() -> None:
    """`\\DeclareMathAlphabet` names a font no browser has. The family is mapped to the nearest alphabet MathJax does have; without this the relative localization paper's `\\mathpzc` reached the page in error colour."""
    from loom.scan.macros import declared_alphabets

    got = declared_alphabets(r"\DeclareMathAlphabet{\mathpzc}{OT1}{pzc}{m}{it}")
    assert {k: v.body for k, v in got.items()} == {"mathpzc": r"\mathcal{#1}"}
    assert got["mathpzc"].args == 1

    unknown = declared_alphabets(r"\DeclareMathAlphabet{\mathodd}{OT1}{zzz}{m}{n}")
    assert unknown["mathodd"].body == r"\mathrm{#1}"  # legible, rather than an error


def test_compatibility_macros_are_published_only_when_a_body_needs_them() -> None:
    """A renderer implements neither `\\scalebox` nor `\\ensuremath`, and an operator defined with them renders as an error; each keeps its content and gives up only presentation."""
    from loom.scan.macros import compatibility_macros

    used = parse_macros(r"\DeclareMathOperator{\sHom}{\scalebox{1.2}{\ensuremath{\mathpzc{Hom}}}}")
    got = compatibility_macros(used)
    assert {k: (v.args, v.body) for k, v in got.items()} == {"ensuremath": (1, "#1"), "scalebox": (2, "#2")}

    assert compatibility_macros(parse_macros(r"\newcommand{\Z}{\mathbb{Z}}")) == {}
