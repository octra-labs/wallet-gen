import { WalletService } from "../services/wallet.service";
import type { DeriveRequest, WalletData } from "../types/wallet";
import { handleErrors } from "./middleware";

export function createApiRoutes(
  service: WalletService
): (req: Request) => Response | Promise<Response | undefined> {
  return async function (request: Request): Promise<Response | undefined> {
    const url = new URL(request.url);
    const { pathname } = url;
    const { method } = request;

    if (method === "POST" && pathname === "/generate") {
      return handleGenerateWallet(service);
    }
    if (method === "POST" && pathname === "/save") {
      return handleSaveWallet(request, service);
    }
    if (method === "POST" && pathname === "/derive") {
      return handleDeriveWallet(request, service);
    }
    return undefined; // Let the server handle it as a 404 or static file
  };
}

function handleGenerateWallet(service: WalletService): Response {
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      for await (const event of service.generateWalletStream()) {
        controller.enqueue(encoder.encode(event));
      }
      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}

const handleSaveWallet = handleErrors(
  async (request: Request, service: WalletService): Promise<Response> => {
    const data: WalletData = await request.json();
    const result = service.saveWalletToFile(data);
    return Response.json(result);
  }
);

const handleDeriveWallet = handleErrors(
  async (request: Request, service: WalletService): Promise<Response> => {
    const data: DeriveRequest = await request.json();
    const result = service.deriveAddress(data);
    return Response.json({ success: true, ...result });
  }
);
