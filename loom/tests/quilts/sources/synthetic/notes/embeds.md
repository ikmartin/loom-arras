# HTML in a Markdown file

A file may use <kbd>ordinary</kbd> HTML, inline and as <abbr title="a run of HTML of its own">a block</abbr>, with $x_i$ beside it and Vector<T> left as a word.

<details open>
<summary>A fold of the file's own</summary>

Markdown still works inside it, with *emphasis* and $y_i$.

</details>

<p align="center" style="position: fixed; inset: 0" class="box"><img src="figure.png" alt="The small figure" width="40"></p>

A video takes the column's width, whatever width it asks for.

<iframe width="560" height="315" src="https://www.youtube.com/embed/loom-fixture" title="A video" frameborder="0" allow="autoplay" referrerpolicy="unsafe-url" allowfullscreen srcdoc="<script>parent.loomHostile = 'srcdoc'</script>" sandbox="allow-top-navigation" onload="loomHostile = 'frame'"></iframe>

## What is not drawn

A frame on an address that is not `https:` shows as the text it is.

<iframe src="http://frames.example/plain"></iframe>

<script>window.loomHostile = 'script'</script>

<img src="no-such-image.png" onerror="window.loomHostile = 'handler'" alt="An image with a handler">

<a id="by-scheme" href="javascript:window.loomHostile='link'">A link by scheme</a>, <a id="by-tab" href="java&#x09;script:window.loomHostile='tab'">one with a tab in it</a>, and $\href{ javascript:window.loomHostile='math'}{a link in a formula}$.
