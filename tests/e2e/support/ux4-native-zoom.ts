import { mkdir, writeFile } from "node:fs/promises";
import {
  chromium,
  expect,
  type BrowserContext,
  type Locator,
  type Page,
  type TestInfo,
} from "@playwright/test";

/** Test-only Chromium page zoom. No CSS zoom, pinch emulation or viewport substitution. */
export async function nativeZoomBrowser(testInfo: TestInfo) {
  const extension = testInfo.outputPath("synthetic-native-zoom-extension");
  await mkdir(extension, { recursive: true });
  await writeFile(
    extension + "/manifest.json",
    JSON.stringify({
      manifest_version: 3,
      name: "Synthetic UX4 native browser zoom test",
      version: "1.0",
      permissions: ["tabs"],
      background: { service_worker: "worker.js" },
    }),
  );
  await writeFile(
    extension + "/worker.js",
    "chrome.runtime.onInstalled.addListener(() => {});\n",
  );
  const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
  const context = await chromium.launchPersistentContext(
    testInfo.outputPath("synthetic-zoom-profile"),
    {
      ...(executablePath ? { executablePath } : {}),
      headless: false,
      viewport: { width: 1280, height: 900 },
      args: [
        "--headless=new",
        "--disable-extensions-except=" + extension,
        "--load-extension=" + extension,
      ],
    },
  );
  const worker =
    context.serviceWorkers()[0] ??
    (await context.waitForEvent("serviceworker"));
  const page = context.pages()[0] ?? (await context.newPage());
  await page.bringToFront();
  const setZoom = async (factor: number) => {
    const actual = await worker.evaluate(
      async ({ origin, factor }) => {
        const tabs = (
          globalThis as unknown as {
            chrome: {
              tabs: {
                query: (query: {
                  url: string;
                }) => Promise<Array<{ id: number }>>;
                setZoom: (id: number, factor: number) => Promise<void>;
                getZoom: (id: number) => Promise<number>;
              };
            };
          }
        ).chrome.tabs;
        const matches = await tabs.query({ url: origin + "/*" });
        if (matches.length !== 1)
          throw new Error("Expected one synthetic application tab");
        await tabs.setZoom(matches[0].id, factor);
        return tabs.getZoom(matches[0].id);
      },
      { origin: new URL(page.url()).origin, factor },
    );
    expect(actual).toBeCloseTo(factor, 8);
    await expect
      .poll(() => page.evaluate(() => window.innerWidth))
      .toBe(1280 / factor);
    await expect
      .poll(() => page.evaluate(() => window.devicePixelRatio))
      .toBeCloseTo(factor, 12);
    return {
      requestedZoom: factor,
      nativeZoomFactor: actual,
      ...(await browserMeasurements(page)),
    };
  };
  return { context, page, setZoom };
}

export function browserMeasurements(page: Page) {
  return page.evaluate(() => ({
    width: window.innerWidth,
    ratio: window.devicePixelRatio,
    documentWidth: document.documentElement.scrollWidth,
    cssZoom: getComputedStyle(document.documentElement).zoom,
    activeElement: document.activeElement?.tagName,
  }));
}

export async function assertDocumentReflow(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    )
    .toBe(true);
}

/** Concrete rendered color samples, not a claim of a complete accessibility audit. */
export async function contrastSample(target: Locator) {
  return target.evaluate((element) => {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 1;
    const context = canvas.getContext("2d")!;
    const rgba = (color: string) => {
      context.clearRect(0, 0, 1, 1);
      context.fillStyle = color;
      context.fillRect(0, 0, 1, 1);
      const pixel = context.getImageData(0, 0, 1, 1).data;
      return [pixel[0], pixel[1], pixel[2], pixel[3] / 255];
    };
    const over = (foreground: number[], background: number[]) =>
      foreground
        .slice(0, 3)
        .map(
          (channel, index) =>
            channel * foreground[3] + background[index] * (1 - foreground[3]),
        )
        .concat(1);
    const ancestors: Element[] = [];
    for (
      let current: Element | null = element;
      current;
      current = current.parentElement
    )
      ancestors.unshift(current);
    let background = [255, 255, 255, 1];
    for (const ancestor of ancestors)
      background = over(
        rgba(getComputedStyle(ancestor).backgroundColor),
        background,
      );
    const style = getComputedStyle(element);
    const luminance = (color: number[]) =>
      color
        .slice(0, 3)
        .map((channel) => {
          const value = channel / 255;
          return value <= 0.04045
            ? value / 12.92
            : ((value + 0.055) / 1.055) ** 2.4;
        })
        .reduce(
          (total, value, index) =>
            total + value * [0.2126, 0.7152, 0.0722][index],
          0,
        );
    const ratio = (color: number[]) => {
      const a = luminance(over(color, background));
      const b = luminance(background);
      return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    };
    return {
      text: element.textContent?.trim().slice(0, 100),
      foreground: style.color,
      background,
      textRatio: ratio(rgba(style.color)),
      outline: style.outlineColor,
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
      focusRatio: ratio(rgba(style.outlineColor)),
      fontSize: style.fontSize,
    };
  });
}

export async function nativeScreenshot(
  context: BrowserContext,
  page: Page,
  testInfo: TestInfo,
  name: string,
) {
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
  const session = await context.newCDPSession(page);
  try {
    const capture = await session.send("Page.captureScreenshot", {
      format: "png",
      fromSurface: false,
      captureBeyondViewport: false,
    });
    await testInfo.attach(name, {
      body: Buffer.from(capture.data, "base64"),
      contentType: "image/png",
    });
  } finally {
    await session.detach();
  }
}
