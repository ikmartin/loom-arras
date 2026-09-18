## Open
- the viewer could generally be sped up and optimized. Many things feel a little slow. Clicking buttons in the settings is laggy. Test out 6 potential optimizations, implement the top 3.
- a toggle in settings for "paper" or "blog" format display, applied globally so that it affects the read display as well as the display of nodes.
- (FOR HUMAN) the modes should be reviewed and heavily modified. This likely needs to be verified and completed by a human.
- color coding in the graph view: currently no color coding at all. should match the color of the taxons, and there should be one place to set these colors.

## Closed
- still some latex errors in the ACGS quilt, I suspect it's from bad parsing of style files or preambles. For example: "generator of the -th factor in the universal base log structure \Spec \big(\bigoplus_{\text{nodes of \ul C}} \NN\arr \kk\big). Our choice" in "acgs-002P/proof". This is likely due to text being lost after an accent: $q$ in the \'etale topology. Then there exist unique lifts $s_x,…$ is published as "in the é" followed directly by the next formula. Everything between the accent and the formula is gone. This is a bug in loom's HTML conversion, not in the preamble. Also possibly due to the presence of a macros inside \text{}. The formula containing \text{nodes of \ul C} shows up as raw TeX. \ul is defined in drafts/main.tex and does reach arras. My guess is that MathJax doesn't expand author macros inside \text{}
- add the option for expandable annotation/comment boxes. Comment boxes and annotations no longer are restricted to live in the right gutter, they appear as color coded highlights on the source text. Clicking them expands them.
- the graph view needs work. the layered view is completely broken for instance, and the nodes shouldn't be draggable in this view. see the broken-graph.png screenshot on desktop for an example of the broken view in a zoom.
- it would be nice to have a local graph view that you can open up which changes based on where you are in the draft. Something like the graph viewer in quartz5 -- maybe it's even portable from that project (https://quartz.jzhao.xyz/).
- links in the references should be clickable
- the accepted, stale, incomplete, and errors pages are bizarre, the incomplete page in particular -- it's called "blockers", it has a "views" panel on the side replicating the strip.
- the tabs view should be retired, keep strip and rail
- clicking anywhere outside of the settings box when the box is expanded should close the box, same behavior for other floating boxes.
- it'd be nice to have something similar to the "hover to preview" functionality that exists in my sitegen. For example, if worked-examples or counter examples or stress tests of even other nodes linked to or are linked from a node I'm viewing, it'd be nice to hover over the links/backlinks to get a preview.
- the audit requires [uses-ledger], the report should include it, and thus it should be returned to the audit mode