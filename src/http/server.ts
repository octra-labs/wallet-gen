import { WalletService } from "../services/wallet.service";
import { createApiRoutes } from "./routes";
import {
  indexHtml,
  logoSvg,
  foundersGroteskFont,
  nationalFont,
  styleCss,
  scriptJs,
} from "./assets";

export function startServer(port: number, walletService: WalletService) {
  const handleApiRequest = createApiRoutes(walletService);

  Bun.serve({
    port,
    hostname: "0.0.0.0",
    async fetch(request: Request): Promise<Response> {
      const url = new URL(request.url);
      const { pathname } = url;

      const apiResponse = await handleApiRequest(request);
      if (apiResponse) {
        return apiResponse;
      }

      if (request.method === "GET") {
        switch (pathname) {
          case "/":
          case "/index.html":
            return new Response(indexHtml, {
              headers: { "Content-Type": "text/html" },
            });

          case "/assets/style.css":
            return new Response(styleCss, {
              headers: { "Content-Type": "text/css" },
            });

          case "/js/script.js":
            return new Response(scriptJs, {
              headers: { "Content-Type": "application/javascript" },
            });

          case "/assets/logo.svg":
            return new Response(logoSvg, {
              headers: { "Content-Type": "image/svg+xml" },
            });

          case "/assets/founders-grotesk-bold.woff2":
            return new Response(foundersGroteskFont, {
              headers: { "Content-Type": "font/woff2" },
            });

          case "/assets/national-regular.woff2":
            return new Response(nationalFont, {
              headers: { "Content-Type": "font/woff2" },
            });
        }
      }

      return new Response("Not Found", { status: 404 });
    },
    error(error: Error): Response {
      console.error(error);
      return new Response("Internal Server Error", { status: 500 });
    },
  });
}
