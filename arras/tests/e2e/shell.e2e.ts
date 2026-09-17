import { expect, test } from "@playwright/test";

const SHELLS = ["a", "c"] as const;

for (const shell of SHELLS) {
  test(`shell ${shell} contains the same elements as the others`, async ({
    page,
  }) => {
    await page.goto(`/master/main?shell=${shell}`);
    await expect(page.locator("html")).toHaveAttribute("data-shell", shell);
    // the view switcher, the document picker, the contents tree, the search affordance and the counts are in every arrangement
    await expect(
      page.getByRole("link", { name: "graph", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("combobox", { name: "Document" }),
    ).toBeVisible();
    await expect(
      page.getByRole("navigation", { name: "Contents" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Search" })).toBeVisible();
    await expect(page.getByTestId("counts")).toContainText("nodes");
  });
}

test("the default shell is the icon strip", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-shell", "c");
});

test("the contents rail scrolls rather than overflowing, and its last entry can be reached", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 320 }); // short enough that the fixture's contents cannot fit
  await page.goto("/master/main");
  const rail = page.getByRole("navigation", { name: "Contents" });
  const box = await rail.evaluate((el) => ({
    scroll: el.scrollHeight,
    client: el.clientHeight,
    overflow: getComputedStyle(el).overflowY,
  }));
  expect(box.overflow).toBe("auto");
  expect(box.scroll).toBeGreaterThan(box.client);
  const last = rail.locator("a").last();
  await last.scrollIntoViewIfNeeded();
  await expect(last).toBeInViewport();
});

test("the contents tree is in document order and stops above paragraph units", async ({
  page,
}) => {
  await page.goto("/master/main");
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
  await page.getByTestId("shell-a").click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("html")).toHaveAttribute("data-shell", "a");

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("html")).toHaveAttribute("data-shell", "a");
});

test("no route reaches an unknown key from review, its incomplete view, or the problems page", async ({
  page,
}) => {
  for (const start of ["/review", "/review?show=incomplete", "/problems"]) {
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
  await expect(page.getByTestId("layout-force")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.getByTestId("gnode-sy-0003").click();
  await expect(
    page.locator("aside").getByRole("link", { name: /Theorem/ }),
  ).toBeVisible();
  const forceEdges = await page.locator("svg path.edge").count();
  expect(forceEdges).toBeGreaterThan(0);

  await page.getByTestId("layout-layered").click();
  await expect(page.getByTestId("layout-layered")).toHaveAttribute(
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

test("the read view has gutters, with the margin annotation in one and the comments in the other", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/master/main");
  await page.waitForSelector(".fragment .env[data-key]");

  const env = page.locator('.fragment .env[data-key="sy-0001"]');
  const margin = env.locator(".node-margin");
  await expect(margin).toContainText("sy-0001");
  await expect(margin).toContainText("accepted");

  const envBox = (await env.boundingBox())!;
  const marginBox = (await margin.boundingBox())!;
  // the annotation sits wholly in the left gutter, ending where the environment's accent rule begins
  expect(marginBox.x + marginBox.width).toBeLessThanOrEqual(envBox.x + 1);

  const comment = page.locator(
    'aside.comment-slot.gutter[data-slot-for="sy-0001"]',
  );
  await expect(comment).toBeVisible();
  const commentBox = (await comment.boundingBox())!;
  // and the comment sits wholly in the right gutter, beginning where the text column ends
  expect(commentBox.x).toBeGreaterThanOrEqual(envBox.x + envBox.width - 1);
  await expect(comment.locator("article.box")).toHaveCount(1);
  // aligned with the node it is about
  expect(Math.abs(commentBox.y - envBox.y)).toBeLessThan(40);

  // the two gutters are the same width, and the text keeps its measure between them
  const host = (await page.locator(".gutters").boundingBox())!;
  const left = envBox.x - host.x;
  const right = host.x + host.width - (envBox.x + envBox.width);
  expect(Math.abs(left - right)).toBeLessThan(2);
  expect(left).toBeGreaterThan(80);
});

test("a comment with sizeable content stays in the text as a box", async ({
  page,
}) => {
  await page.route("**/build/manifest.json", async (route) => {
    const res = await route.fetch();
    const m = await res.json();
    m.annotations["a-2026-09-16-0006"].body_html =
      "<p>" +
      "This comment says a great deal about the involution and its fixed locus. ".repeat(
        8,
      ) +
      "</p>";
    await route.fulfill({ response: res, json: m });
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/master/main");
  await page.waitForSelector(".fragment .env[data-key]");

  const inline = page.locator(
    'aside.comment-slot.inline[data-slot-for="sy-0001"]',
  );
  await expect(inline).toBeVisible();
  await expect(
    page.locator('aside.comment-slot.gutter[data-slot-for="sy-0001"]'),
  ).toHaveCount(0);

  // in the flow: as wide as the text column, and below the node rather than beside it
  const env = (await page
    .locator('.fragment .env[data-key="sy-0001"]')
    .boundingBox())!;
  const box = (await inline.boundingBox())!;
  expect(box.x).toBeGreaterThanOrEqual(env.x - 1);
  expect(box.width).toBeGreaterThan(env.width / 2);
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
  await expect(page.getByTestId("counts")).toBeInViewport();
});

test("the contents rail shows its scrollbar only while it is in use", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 340 });
  await page.goto("/master/main");
  const rail = page.getByRole("navigation", { name: "Contents" });
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
  expect(rows.length).toBe(6);
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
