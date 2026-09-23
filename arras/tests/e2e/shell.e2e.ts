import { expect, test } from "@playwright/test";

/** The contents hang off the open document behind a `show` disclosure (plan 0.13.1). */
async function openContents(page: import("@playwright/test").Page) {
  const toggle = page.getByTestId("contents-toggle");
  await toggle.waitFor({ state: "visible" });
  if ((await toggle.getAttribute("aria-expanded")) === "false") await toggle.click();
  await page.getByRole("navigation", { name: "Contents" }).waitFor();
}

test("the shell carries the views, the documents, the contents, search and the problems glyph", async ({
  page,
}) => {
  // One arrangement. There were two, and the second fell behind on the first panel change that was not made twice.
  await page.goto("/master/main");
  await expect(page.getByRole("link", { name: "graph", exact: true })).toBeVisible();
  await expect(page.getByTestId("docs-drafts")).toBeVisible();
  await openContents(page);
  await expect(page.getByRole("navigation", { name: "Contents" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Search" })).toBeVisible();
  await expect(page.getByTestId("problems-glyph")).toHaveAttribute("title", /^problems: /);
});

test("the side panel scrolls rather than overflowing, and the contents' last entry can be reached", async ({
  page,
}) => {
  // One scroll region, and it is the panel (plan 0.13 §7). The contents tree carried the only scrollbar until the
  // Library group was added below it, at which point what got squeezed was the tree and the sections under it went
  // off the bottom of a column that could not scroll.
  await page.setViewportSize({ width: 1280, height: 320 }); // short enough that the fixture's panel cannot fit
  await page.goto("/master/main");
  await openContents(page);
  const sections = page.locator(".panel .sections");
  const box = await sections.evaluate((el) => ({
    scroll: el.scrollHeight,
    client: el.clientHeight,
    overflow: getComputedStyle(el).overflowY,
  }));
  expect(box.overflow).toBe("auto");
  expect(box.scroll).toBeGreaterThan(box.client);
  const last = page.getByRole("navigation", { name: "Contents" }).locator("a").last();
  await last.scrollIntoViewIfNeeded();
  await expect(last).toBeInViewport();
  // and the write target is pinned below the scroll rather than scrolled away with it
  await expect(page.getByTestId("session-footer")).toBeInViewport();
});

test("the side panel collapses, and the column goes with it", async ({ page }) => {
  // It collapses independently of the split and goes first: on a narrow window it is the column a reader needs least.
  await page.goto("/master/main");
  await openContents(page);
  const panel = page.locator(".panel");
  const wide = (await panel.boundingBox())!.width;
  await page.getByTestId("panel-fold").click();
  await expect(page.getByRole("navigation", { name: "Contents" })).toBeHidden();
  const narrow = (await panel.boundingBox())!.width;
  expect(narrow).toBeLessThan(wide / 3); // the column itself goes, not just its contents
  // and it comes back
  await page.getByTestId("panel-fold").click();
  await expect(page.getByRole("navigation", { name: "Contents" })).toBeVisible();
});

test("the contents tree is in document order and stops above paragraph units", async ({
  page,
}) => {
  await page.goto("/master/main");
  await openContents(page);
  const entries = page
    .getByRole("navigation", { name: "Contents" })
    .locator("a");
  await expect(entries.first()).toContainText("Introduction");
  const texts = await entries.allInnerTexts();
  expect(texts.some((t) => t.includes("Results"))).toBe(true);
  expect(texts.some((t) => t.includes("paragraph"))).toBe(false);
});

test("a contents entry scrolls the document instead of navigating away", async ({
  page,
}) => {
  await page.goto("/master/main");
  await openContents(page);
  const entry = page
    .getByRole("navigation", { name: "Contents" })
    .getByRole("link", { name: /Results/ });
  await entry.click();
  await expect(page).toHaveURL(/\/master\/main#sy-0200$/);
  await expect(page.locator("#sy-0200")).toBeInViewport();
});

test("the contents rail always marks where the reader is, and the mark follows the scroll", async ({
  page,
}) => {
  // It used to be driven by location.hash: it appeared only once someone clicked an entry and then never moved,
  // and an entry whose key is not slug-shaped never matched the hash at all.
  await page.goto("/master/main");
  await openContents(page);
  const contents = page.getByRole("navigation", { name: "Contents" });
  await contents.getByRole("link").first().waitFor();

  const marked = async () =>
    contents.locator('a[aria-current="true"]').textContent();
  expect(await contents.locator('a[aria-current="true"]').count()).toBe(1); // showing before any scrolling

  const first = await marked();
  const ids = await page
    .locator("main section[id]")
    .evaluateAll((els) => els.map((e) => e.id));
  expect(ids.length).toBeGreaterThan(1);

  await page.locator(`#${ids[ids.length - 1]}`).scrollIntoViewIfNeeded();
  await page.waitForTimeout(150);
  expect(await contents.locator('a[aria-current="true"]').count()).toBe(1); // still exactly one
  expect(await marked()).not.toBe(first); // and it moved

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(150);
  expect(await marked()).toBe(first); // scrolling back returns it
});

test("every icon in the strip is drawn, not a text glyph", async ({ page }) => {
  // unicode marks rendered at whatever weight and baseline a font chose, so a column of them sat unevenly
  await page.goto("/");
  const strip = page.getByRole("navigation", { name: "Views" });
  const links = strip.locator("a");
  await links.first().waitFor(); // count() does not wait, and the strip is not there until the app has started
  const n = await links.count();
  expect(n).toBeGreaterThan(3);
  for (let i = 0; i < n; i++) {
    await expect(links.nth(i).locator("svg")).toHaveCount(1);
    expect((await links.nth(i).innerText()).trim()).toBe("");
  }
  await expect(
    strip.getByRole("button", { name: "Search" }).locator("svg"),
  ).toHaveCount(1);
});

test("a heading links to its node, and an equation reference lands on the equation", async ({
  page,
}) => {
  await page.goto("/master/main");
  const head = page.locator("#sy-0200 > h1");
  await expect(head.locator("a.heading-link")).toHaveAttribute(
    "href",
    "/node/sy-0200",
  );
  const eq = page.locator("a.ref-eq").first();
  await expect(eq).toHaveAttribute("href", /^#sy-\d+/);
  const target = await eq.getAttribute("href");
  await expect(page.locator(target!)).toHaveCount(1);
});

test("the display preferences survive a reload and change the document", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByTestId("settings-toggle").click();
  await page.getByTestId("theme-dark").click();
  await page.getByTestId("size-l").click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("html")).toHaveAttribute("data-size", "l");

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("html")).toHaveAttribute("data-size", "l");
});

test("no route reaches an unknown key from review or the problems page", async ({
  page,
}) => {
  for (const start of ["/review", "/problems"]) {
    await page.goto(start);
    await expect(page.locator('main a[href^="/node/"]').first()).toBeAttached();
    const hrefs = await page
      .locator('main a[href^="/node/"]')
      .evaluateAll((els) => [
        ...new Set(
          els.map((e) => (e as HTMLAnchorElement).getAttribute("href")!),
        ),
      ]);
    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) {
      await page.goto(href.split("#")[0]);
      await expect(
        page.locator("main h1").first(),
        `${start} links to ${href}`,
      ).not.toHaveText("Unknown key");
    }
  }
});

test("the graph toggle keeps the selection and both layouts draw their edges", async ({
  page,
}) => {
  await page.goto("/graph");
  await expect(page.getByTestId("layout-dots")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.getByTestId("gnode-sy-0003").click();
  await expect(
    page.locator("aside").getByRole("link", { name: /Theorem/ }),
  ).toBeVisible();
  const forceEdges = await page.locator("svg path.edge").count();
  expect(forceEdges).toBeGreaterThan(0);

  await page.getByTestId("layout-box").click();
  await expect(page.getByTestId("layout-box")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(
    page.locator("aside").getByRole("link", { name: /Theorem/ }),
  ).toBeVisible();
  // layered leaves out an edge from a node into the section that contains it, which ELK cannot route into an ancestor, so it can draw fewer
  await expect.poll(() => page.locator("svg path.edge").count()).toBeGreaterThan(0);
  expect(await page.locator("svg path.edge").count()).toBeLessThanOrEqual(forceEdges);
});

test("the key gutter carries the id and the state beside the node", async ({
  page,
}) => {
  // The comment gutter went with the `margin` placement; the left gutter, which names the node and its state, stays --
  // behind Settings > Show ids, which is off by default, so the test turns it on the way a reader would.
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.addInitScript(() => {
    try {
      localStorage.setItem("arras.prefs", JSON.stringify({ ids: true }));
    } catch {
      /* storage unavailable: the gutter stays hidden and the assertions below say so */
    }
  });
  await page.goto("/master/main");
  await page.waitForSelector(".fragment .env[data-key]");

  const env = page.locator('.fragment .env[data-key="sy-0001"]');
  const margin = env.locator(".node-margin");
  await expect(margin).toContainText("sy-0001");
  await expect(margin).toContainText("accepted");

  const envBox = (await env.boundingBox())!;
  const marginBox = (await margin.boundingBox())!;
  // it sits wholly in the left gutter, ending where the environment's accent rule begins
  expect(marginBox.x + marginBox.width).toBeLessThanOrEqual(envBox.x + 1);
  // and an id is never broken across lines, however narrow the gutter gets
  const lines = await margin.locator(".mid").evaluate((e) => e.getClientRects().length);
  expect(lines).toBe(1);
});


test("the shell fits the window: nothing in a rail falls below the fold", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.waitForSelector("main h1");

  const fit = await page.evaluate(() => ({
    inner: window.innerHeight,
    scroll: document.documentElement.scrollHeight,
  }));
  expect(fit.scroll).toBeLessThanOrEqual(fit.inner); // a rail is `height: 100vh`, and its padding must count inside that

  // the two things at the foot of the shell are reachable without scrolling
  await expect(page.getByTestId("settings-toggle")).toBeInViewport();
  await expect(page.getByTestId("problems-glyph")).toBeInViewport();
  await expect(page.getByTestId("session-footer")).toBeInViewport();
});

test("the side panel shows its scrollbar only while it is in use", async ({
  page,
}) => {
  // The panel is the scroll region now, so the rule about a grey stripe down the side of every page belongs to it.
  await page.setViewportSize({ width: 1440, height: 340 });
  await page.goto("/master/main");
  const rail = page.locator(".panel .sections");
  await expect(rail).toBeVisible();

  const atRest = await rail.evaluate(
    (el) => getComputedStyle(el).scrollbarColor,
  );
  expect(atRest).toContain("rgba(0, 0, 0, 0)"); // the thumb is transparent until the rail is used

  await rail.hover();
  await expect
    .poll(async () =>
      rail.evaluate((el) => getComputedStyle(el).scrollbarColor),
    )
    .not.toContain("rgba(0, 0, 0, 0) rgba(0, 0, 0, 0)");
});

test("the settings panel puts every row on one line, label included, with nothing cut off", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByTestId("settings-toggle").click();
  const rows = await page.getByTestId("settings-panel").evaluate((el) => {
    const panel = el.getBoundingClientRect();
    return [...el.querySelectorAll(".row")].map((f) => {
      const label = f.querySelector(".lbl") as HTMLElement;
      const buttons = [...f.querySelectorAll("button")].map((b) =>
        b.getBoundingClientRect(),
      );
      const mid = (r: DOMRect) => r.top + r.height / 2;
      return {
        label: label.textContent ?? "",
        lines: new Set(buttons.map((r) => Math.round(r.top))).size,
        // the label shares the row's line: its middle falls inside every button's box
        inline: buttons.every(
          (r) =>
            mid(label.getBoundingClientRect()) > r.top &&
            mid(label.getBoundingClientRect()) < r.bottom,
        ),
        spill: buttons.filter(
          (r) => r.right > panel.right || r.left < panel.left,
        ).length,
      };
    });
  });
  expect(rows.length).toBe(8); // type, size, width, theme, format, comments, show ids, panes
  for (const r of rows) {
    expect(r.lines, `the ${r.label} row wraps`).toBe(1);
    expect(r.inline, `the ${r.label} label is not on the row's line`).toBe(
      true,
    );
    expect(r.spill, `the ${r.label} row is clipped by the panel`).toBe(0);
  }
});

test("the icon strip offers each destination exactly once", async ({
  page,
}) => {
  await page.goto("/");
  await page.waitForSelector("main h1"); // until the manifest arrives the read icon has no document to point at
  const strip = page.getByRole("navigation", { name: "Views" });
  const hrefs = await strip
    .locator("a[href]")
    .evaluateAll((els) => els.map((e) => e.getAttribute("href")));
  expect(new Set(hrefs).size).toBe(hrefs.length); // no two icons go to the same place
  expect(hrefs).toContain("/");
});

test("a display block never scrolls vertically", async ({ page }) => {
  await page.goto("/master/main");
  await page.waitForSelector(".fragment .math.display");
  await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const els = [
      ...document.querySelectorAll(".fragment .math.display"),
    ] as HTMLElement[];
    return {
      n: els.length,
      // naming one axis makes the browser compute the other to `auto`, and MathJax's hidden accessibility copy is taller than the box, which grew a scrollbar beside a formula that fitted
      axes: [...new Set(els.map((el) => getComputedStyle(el).overflowY))],
      bars: els.filter((el) => el.offsetWidth > el.clientWidth).length,
    };
  });
  expect(r.n).toBeGreaterThan(0);
  expect(r.axes).toEqual(["hidden"]);
  expect(r.bars).toBe(0);
});
