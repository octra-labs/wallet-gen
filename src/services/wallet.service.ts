import fs from "fs";
import * as bip39 from "bip39";
import nacl from "tweetnacl";
import type {
  WalletData,
  NetworkDerivation,
  DeriveRequest,
} from "../types/wallet";
import * as crypto from "../core/crypto";
import * as hdWallet from "../core/hd-wallet";
import {
  bufferToHex,
  base64Encode,
  hexToBuffer,
  sleep,
} from "../utils/converters";

export class WalletService {
  async *generateWalletStream(): AsyncGenerator<string> {
    try {
      yield this.streamEvent("Generating entropy...");
      const entropy = crypto.generateEntropy(128);
      await sleep(200);

      yield this.streamEvent("Creating mnemonic phrase...");
      const mnemonic = bip39.entropyToMnemonic(entropy.toString("hex"));
      const mnemonicWords = mnemonic.split(" ");
      await sleep(200);

      yield this.streamEvent("Deriving seed from mnemonic...");
      const seed = bip39.mnemonicToSeedSync(mnemonic);
      await sleep(200);

      yield this.streamEvent("Deriving master key...");
      const { masterPrivateKey, masterChainCode } =
        hdWallet.deriveMasterKey(seed);
      await sleep(200);

      yield this.streamEvent("Creating Ed25519 keypair...");
      const keyPair = nacl.sign.keyPair.fromSeed(masterPrivateKey);
      const privateKeyRaw = Buffer.from(keyPair.secretKey.slice(0, 32));
      const publicKeyRaw = Buffer.from(keyPair.publicKey);
      await sleep(200);

      yield this.streamEvent("Generating Octra address...");
      const address = crypto.createOctraAddress(publicKeyRaw);
      await sleep(200);

      if (!crypto.verifyAddressFormat(address)) {
        throw new Error("Invalid address format generated");
      }
      yield this.streamEvent("Address generated and verified.");
      await sleep(200);

      yield this.streamEvent("Testing signature functionality...");
      const testMessage = `{"from":"${address}","to":"test","amount":"1","nonce":0}`;
      const messageBytes = Buffer.from(testMessage, "utf8");
      const signature = crypto.sign(messageBytes, keyPair.secretKey);
      const signatureValid = crypto.verifySignature(
        messageBytes,
        signature,
        keyPair.publicKey
      );
      yield this.streamEvent(
        signatureValid ? "Signature test passed." : "Signature test failed."
      );
      await sleep(200);

      const walletData: WalletData = {
        mnemonic: mnemonicWords,
        seed_hex: bufferToHex(seed),
        master_chain_hex: bufferToHex(masterChainCode),
        private_key_hex: bufferToHex(privateKeyRaw),
        public_key_hex: bufferToHex(publicKeyRaw),
        private_key_b64: base64Encode(privateKeyRaw),
        public_key_b64: base64Encode(publicKeyRaw),
        address: address,
        entropy_hex: bufferToHex(entropy),
        test_message: testMessage,
        test_signature: base64Encode(signature),
        signature_valid: signatureValid,
      };

      yield this.streamEvent("Wallet generation complete!", walletData);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "An unknown error occurred";
      yield this.streamEvent(`ERROR: ${errorMessage}`);
    }
  }

  saveWalletToFile(walletData: WalletData): {
    success: true;
    filename: string;
  } {
    const timestamp = Math.floor(Date.now() / 1000);
    const filename = `octra_wallet_${walletData.address.slice(
      -8
    )}_${timestamp}.txt`;
    const content = this.formatWalletFileContent(walletData);
    fs.writeFileSync(filename, content);
    return { success: true, filename };
  }

  deriveAddress(request: DeriveRequest): {
    address: string;
    path: string;
    network_type_name: string;
  } {
    const { seed_hex, network_type = 0, index = 0 } = request;
    const seed = hexToBuffer(seed_hex);

    // This derivation logic can be expanded as needed
    const derivation = this.deriveForNetwork(seed, network_type, index);

    const pathString = derivation.path
      .map((i) => (i & 0x7fffffff).toString() + (i & 0x80000000 ? "'" : ""))
      .join("/");

    return {
      address: derivation.address,
      path: pathString,
      network_type_name: derivation.networkTypeName,
    };
  }

  // --- Private Helper Methods ---

  private streamEvent(status: string, wallet?: WalletData): string {
    const data = wallet ? { status, wallet } : { status };
    return `data: ${JSON.stringify(data)}\n\n`;
  }

  private formatWalletFileContent(data: WalletData): string {
    return `OCTRA WALLET
==================================================

SECURITY WARNING: KEEP THIS FILE SECURE AND NEVER SHARE YOUR PRIVATE KEY

Generated: ${new Date().toISOString().replace("T", " ").slice(0, 19)}
Address Format: oct + Base58(SHA256(pubkey))

Mnemonic: ${data.mnemonic.join(" ")}
Private Key (B64): ${data.private_key_b64}
Public Key (B64): ${data.public_key_b64}
Address: ${data.address}

Technical Details:
Entropy: ${data.entropy_hex}
Signature Algorithm: Ed25519
Derivation: BIP39-compatible (PBKDF2-HMAC-SHA512, 2048 iterations)
`;
  }

  private deriveForNetwork(
    seed: Buffer,
    networkType: number,
    index: number
  ): NetworkDerivation {
    const path = [
      0x80000000 + 345, // Purpose (Octra specific)
      0x80000000 + networkType, // Coin type
      0x80000000 + 0, // Account
      0, // Change
      index, // Address index
    ];

    const { key: derivedKey, chain: derivedChain } = hdWallet.derivePath(
      seed,
      path
    );
    const keyPair = nacl.sign.keyPair.fromSeed(derivedKey);
    const address = crypto.createOctraAddress(Buffer.from(keyPair.publicKey));

    return {
      privateKey: derivedKey,
      chainCode: derivedChain,
      publicKey: Buffer.from(keyPair.publicKey),
      address,
      path,
      networkTypeName: this.getNetworkTypeName(networkType),
      network: 0,
      contract: 0,
      account: 0,
      index,
    };
  }

  private getNetworkTypeName(networkType: number): string {
    // This can be expanded into a more sophisticated system
    const names: { [key: number]: string } = {
      0: "MainCoin",
      1: "SubCoin",
      2: "Contract",
      3: "Subnet",
      4: "Account",
    };
    return names[networkType] || `Unknown (${networkType})`;
  }
}
