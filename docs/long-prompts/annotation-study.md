Prompt #1

Previously I asked you to run a study on all reading views that existed in loom. This turned up ~ 7 different views with various problems, which 0.13 sought to unify, simplify, and improve.

I now want you to study the annotation system. The end goal of this study is to create a plan for revising the annotation system -- simplifying it where possible, making it more visually appealing/informative, and generally making it as usable as possible. For the purposes of this study, an annotation consists of the "type" (question, suggestion, etc) the anchor type (text, locator in a pdf, etc), the target type (node, pdf, document) and the styling (color, underlined vs not, highlighted, etc). So it is a tuple (type, anchor, target, styling). Consider this definition and suggest an improvement if you can think of one, if your suggested definition differs significantly from mine, then pause to discuss before proceeding with the rest of this prompt. Perhaps an "interaction type" should also be included, but I think all annotations are clicked.

First, determine how many distinct annotations exist in loom today. How many visual styles are there? How many different interaction types are there? What is the overlap in functionality between the different types (do we need both comment and note, for example)? How many different colors are there?

Once you have this list, propose an adaptation of the 6 visual principles from 0.14 to the annotation system. In particular there should be at least one principle targeted at the reduction of visual noise. Let's discuss them.

Prompt #2

Critique the set of annotations that exist todayt on the basis of the principles. Also critique the annotation system as a whole on the basis of design. Some suggested questions to ask: does every annotation type need its own visual style (no, is my opinion)? What style best achieves the 2-pronged goal of saying "this text is annotated" while also minimizing the effect on readability of the underlying content? Propose your own questions for the critique too and then evaluate the annotation/annotation system against those questions.

With that done, propose a fix list. What can/should be merged based on the critique? What can be done to fix the style and readability of an annotation as it appears on the text? What can be done to make the annotation popup box more usable/more simple? What can be done to make the add annotation box more usable/more simple? For each propose fix, explain what the error is and how the fix resolves it in no more than two sentences.

Finally, create a demo at a temporary claude url with one row per annotation type. Show two before slides: one showing the annotation on the text (the highlighting, color, underlining, etc), another showing the annotation popup box. Then show two corresponding "after" slides with all fixes to that annotation applied.

If an annotation is to be merged into another annotation, show the identical "after" slides in both rows.

Additionally include the annotation edit box as it appears today ("before") and the proposed annotation edit box with all fixes applied ("after) as the final row.

Prompt #3

Sometimes an annotation on a node only makes sense in context. A simple example: a lemma ex-0002 in a document draft1.tex is redundant, it is already covered by ex-0001. An annotation pointing out that ex-0002 is redundant only makes sense in the context of draft1.tex, so while the annotation may appear to text found in node ex-0002, it should only be shown when the whole of draft1.tex is in view. Do you agree?