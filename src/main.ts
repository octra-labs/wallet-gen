import { startServer } from "./http/server";
import { WalletService } from "./services/wallet.service";

const PORT = 8888;
const walletService = new WalletService();

startServer(PORT, walletService);

console.log(`OCTRA Wallet Generator running on http://localhost:${PORT}`);
