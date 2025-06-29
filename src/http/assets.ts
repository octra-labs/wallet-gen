export const indexHtml = await Bun.file("index.html").text();
export const logoSvg = await Bun.file("assets/logo.svg").text();
export const styleCss = await Bun.file("assets/style.css").text(); 
export const scriptJs = await Bun.file("js/script.js").text(); 
export const foundersGroteskFont = await Bun.file(
  "assets/founders-grotesk-bold.woff2"
).arrayBuffer();
export const nationalFont = await Bun.file(
  "assets/national-regular.woff2"
).arrayBuffer();
