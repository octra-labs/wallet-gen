import crypto from "crypto";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import nacl from "tweetnacl";
import bip39 from "bip39";

import indexHtml from "./static/index.html" with { type: "text" };
import logoSvg from "./static/logo.svg" with { type: "text" };
import foundersGroteskFontPath from "./static/founders-grotesk-bold.woff2" with { type: "file" };
import nationalFontPath from "./static/national-regular.woff2" with { type: "file" };

const __filename: string = fileURLToPath(import.meta.url);
const __dirname: string = path.dirname(__filename);

let foundersGroteskFont: ArrayBuffer;
let nationalFont: ArrayBuffer;

async function loadAssets() {
  try {
    foundersGroteskFont = await Bun.file(foundersGroteskFontPath).arrayBuffer();
    nationalFont = await Bun.file(nationalFontPath).arrayBuffer();
  } catch (error) {
    console.error("Failed to load assets:", error);
  }
}

interface MasterKey {
  masterPrivateKey: Buffer;
  masterChainCode: Buffer;
}

interface ChildKey {
  childPrivateKey: Buffer;
  childChainCode: Buffer;
}

interface DerivedPath {
  key: Buffer;
  chain: Buffer;
}

interface NetworkDerivation {
  privateKey: Buffer;
  chainCode: Buffer;
  publicKey: Buffer;
  address: string;
  path: number[];
  networkTypeName: string;
  network: number;
  contract: number;
  account: number;
  index: number;
}

interface WalletData {
  mnemonic: string[];
  seed_hex: string;
  master_chain_hex: string;
  private_key_hex: string;
  public_key_hex: string;
  private_key_b64: string;
  public_key_b64: string;
  address: string;
  entropy_hex: string;
  test_message: string;
  test_signature: string;
  signature_valid: boolean;
}

interface DeriveRequest {
  seed_hex: string;
  network_type?: number;
  index?: number;
}

const BASE58_ALPHABET: string =
  "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

// Helper functions
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function bufferToHex(buffer: Buffer | Uint8Array): string {
  return Buffer.from(buffer).toString("hex");
}

function hexToBuffer(hex: string): Buffer {
  return Buffer.from(hex, "hex");
}

function base64Encode(buffer: Buffer | Uint8Array): string {
  return Buffer.from(buffer).toString("base64");
}

// Base58 encoding for octra addresses
function base58Encode(buffer: Buffer): string {
  if (buffer.length === 0) return "";

  let num: bigint = BigInt("0x" + buffer.toString("hex"));
  let encoded: string = "";

  while (num > 0n) {
    const remainder: bigint = num % 58n;
    num = num / 58n;
    encoded = BASE58_ALPHABET[Number(remainder)] + encoded;
  }

  // Handle leading zeros
  for (let i = 0; i < buffer.length && buffer[i] === 0; i++) {
    encoded = "1" + encoded;
  }

  return encoded;
}

// Generate entropy using crypto.randomBytes
function generateEntropy(strength: number = 128): Buffer {
  if (![128, 160, 192, 224, 256].includes(strength)) {
    throw new Error("Strength must be 128, 160, 192, 224 or 256 bits");
  }
  return crypto.randomBytes(strength / 8);
}

// Derive master key using HMAC-SHA512 with "Octra seed"
function deriveMasterKey(seed: Buffer): MasterKey {
  const key: Buffer = Buffer.from("Octra seed", "utf8");
  const mac: Buffer = crypto.createHmac("sha512", key).update(seed).digest();

  const masterPrivateKey: Buffer = mac.slice(0, 32);
  const masterChainCode: Buffer = mac.slice(32, 64);

  return { masterPrivateKey, masterChainCode };
}

// HD key derivation for Ed25519
function deriveChildKeyEd25519(
  privateKey: Buffer,
  chainCode: Buffer,
  index: number
): ChildKey {
  let data: Buffer;

  if (index >= 0x80000000) {
    // Hardened derivation
    data = Buffer.concat([
      Buffer.from([0x00]),
      privateKey,
      Buffer.from([
        (index >>> 24) & 0xff,
        (index >>> 16) & 0xff,
        (index >>> 8) & 0xff,
        index & 0xff,
      ]),
    ]);
  } else {
    // Non-hardened derivation
    const keyPair = nacl.sign.keyPair.fromSeed(privateKey);
    const publicKey: Buffer = Buffer.from(keyPair.publicKey);
    data = Buffer.concat([
      publicKey,
      Buffer.from([
        (index >>> 24) & 0xff,
        (index >>> 16) & 0xff,
        (index >>> 8) & 0xff,
        index & 0xff,
      ]),
    ]);
  }

  const mac: Buffer = crypto
    .createHmac("sha512", chainCode)
    .update(data)
    .digest();
  const childPrivateKey: Buffer = mac.slice(0, 32);
  const childChainCode: Buffer = mac.slice(32, 64);

  return { childPrivateKey, childChainCode };
}

// Derive path from seed
function derivePath(seed: Buffer, path: number[]): DerivedPath {
  const { masterPrivateKey, masterChainCode }: MasterKey =
    deriveMasterKey(seed);
  let key: Buffer = masterPrivateKey;
  let chain: Buffer = masterChainCode;

  for (const index of path) {
    const derived: ChildKey = deriveChildKeyEd25519(key, chain, index);
    key = derived.childPrivateKey;
    chain = derived.childChainCode;
  }

  return { key, chain };
}

// Get network type name
function getNetworkTypeName(networkType: number): string {
  switch (networkType) {
    case 0:
      return "MainCoin";
    case 1:
      return `SubCoin ${networkType}`;
    case 2:
      return `Contract ${networkType}`;
    case 3:
      return `Subnet ${networkType}`;
    case 4:
      return `Account ${networkType}`;
    default:
      return `Unknown ${networkType}`;
  }
}

// Derive for specific network
function deriveForNetwork(
  seed: Buffer,
  networkType: number = 0,
  network: number = 0,
  contract: number = 0,
  account: number = 0,
  index: number = 0,
  token: number = 0,
  subnet: number = 0
): NetworkDerivation {
  const coinType: number = networkType === 0 ? 0 : networkType;

  const basePath: number[] = [
    0x80000000 + 345, // Purpose
    0x80000000 + coinType, // Coin type
    0x80000000 + network, // Network
  ];

  const contractPath: number[] = [0x80000000 + contract, 0x80000000 + account];
  const optionalPath: number[] = [0x80000000 + token, 0x80000000 + subnet];
  const finalPath: number[] = [index];

  const fullPath: number[] = [
    ...basePath,
    ...contractPath,
    ...optionalPath,
    ...finalPath,
  ];

  const { key: derivedKey, chain: derivedChain }: DerivedPath = derivePath(
    seed,
    fullPath
  );

  const keyPair = nacl.sign.keyPair.fromSeed(derivedKey);
  const derivedAddress: string = createOctraAddress(
    Buffer.from(keyPair.publicKey)
  );

  return {
    privateKey: derivedKey,
    chainCode: derivedChain,
    publicKey: Buffer.from(keyPair.publicKey),
    address: derivedAddress,
    path: fullPath,
    networkTypeName: getNetworkTypeName(networkType),
    network,
    contract,
    account,
    index,
  };
}

// Create octra address
function createOctraAddress(publicKey: Buffer): string {
  const hash: Buffer = crypto.createHash("sha256").update(publicKey).digest();
  const base58Hash: string = base58Encode(hash);
  return "oct" + base58Hash;
}

// Verify address format
function verifyAddressFormat(address: string): boolean {
  if (!address.startsWith("oct")) return false;
  if (address.length !== 47) return false;

  const base58Part: string = address.slice(3);
  for (const char of base58Part) {
    if (!BASE58_ALPHABET.includes(char)) return false;
  }

  return true;
}

// Route handlers
async function handleGenerateWallet(): Promise<Response> {
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();

      try {
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({ status: "Generating entropy..." })}\n\n`
          )
        );
        await sleep(200);

        const entropy: Buffer = generateEntropy(128);
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({ status: "Entropy generated" })}\n\n`
          )
        );
        await sleep(200);

        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              status: "Creating mnemonic phrase...",
            })}\n\n`
          )
        );
        await sleep(200);

        const mnemonic: string = bip39.entropyToMnemonic(
          entropy.toString("hex")
        );
        const mnemonicWords: string[] = mnemonic.split(" ");
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({ status: "Mnemonic created" })}\n\n`
          )
        );
        await sleep(200);

        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              status: "Deriving seed from mnemonic...",
            })}\n\n`
          )
        );
        await sleep(200);

        const seed: Buffer = bip39.mnemonicToSeedSync(mnemonic);
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({ status: "Seed derived" })}\n\n`
          )
        );
        await sleep(200);

        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({ status: "Deriving master key..." })}\n\n`
          )
        );
        await sleep(200);

        const { masterPrivateKey, masterChainCode }: MasterKey =
          deriveMasterKey(seed);
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({ status: "Master key derived" })}\n\n`
          )
        );
        await sleep(200);

        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              status: "Creating Ed25519 keypair...",
            })}\n\n`
          )
        );
        await sleep(200);

        const keyPair = nacl.sign.keyPair.fromSeed(masterPrivateKey);
        const privateKeyRaw: Buffer = Buffer.from(
          keyPair.secretKey.slice(0, 32)
        );
        const publicKeyRaw: Buffer = Buffer.from(keyPair.publicKey);

        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({ status: "Keypair created" })}\n\n`
          )
        );
        await sleep(200);

        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              status: "Generating octra address...",
            })}\n\n`
          )
        );
        await sleep(200);

        const address: string = createOctraAddress(publicKeyRaw);

        if (!verifyAddressFormat(address)) {
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                status: "ERROR: Invalid address format generated",
              })}\n\n`
            )
          );
          controller.close();
          return;
        }

        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              status: "Address generated and verified",
            })}\n\n`
          )
        );
        await sleep(200);

        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              status: "Testing signature functionality...",
            })}\n\n`
          )
        );
        await sleep(200);

        const testMessage: string =
          '{"from":"test","to":"test","amount":"1000000","nonce":1}';
        const messageBytes: Buffer = Buffer.from(testMessage, "utf8");
        const signature: Uint8Array = nacl.sign.detached(
          messageBytes,
          keyPair.secretKey
        );
        const signatureB64: string = base64Encode(signature);

        let signatureValid: boolean = false;
        try {
          signatureValid = nacl.sign.detached.verify(
            messageBytes,
            signature,
            keyPair.publicKey
          );
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({ status: "Signature test passed" })}\n\n`
            )
          );
        } catch (error: any) {
          console.error("Signature test failed:", error);
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({ status: "Signature test failed" })}

`
            )
          );
        }

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
          test_signature: signatureB64,
          signature_valid: signatureValid,
        };

        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              status: "Wallet generation complete!",
              wallet: walletData,
            })}\n\n`
          )
        );
        controller.close();
      } catch (error: any) {
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({ status: "ERROR: " + error.message })}\n\n`
          )
        );
        controller.close();
      }
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

async function handleSaveWallet(request: Request): Promise<Response> {
  try {
    const data: WalletData = await request.json();
    const timestamp: number = Math.floor(Date.now() / 1000);
    const filename: string = `octra_wallet_${data.address.slice(
      -8
    )}_${timestamp}.txt`;

    const content: string = `octra wallet
${"=".repeat(50)}

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

    await fs.promises.writeFile(filename, content);

    return Response.json({
      success: true,
      filename: filename,
      content: content,
    });
  } catch (error: any) {
    return Response.json(
      {
        success: false,
        error: error.message,
      },
      { status: 500 }
    );
  }
}

async function handleDeriveWallet(request: Request): Promise<Response> {
  try {
    const {
      seed_hex,
      network_type = 0,
      index = 0,
    }: DeriveRequest = await request.json();

    const seed: Buffer = hexToBuffer(seed_hex);
    const derived: NetworkDerivation = deriveForNetwork(
      seed,
      network_type,
      0, // network
      0, // contract
      0, // account
      index
    );

    const pathString: string = derived.path
      .map(
        (i: number) => (i & 0x7fffffff).toString() + (i & 0x80000000 ? "'" : "")
      )
      .join("/");

    return Response.json({
      success: true,
      address: derived.address,
      path: pathString,
      network_type_name: derived.networkTypeName,
    });
  } catch (error: any) {
    return Response.json({
      success: false,
      error: error.message,
    });
  }
}

function getContentType(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  switch (ext) {
    case '.html': return 'text/html';
    case '.svg': return 'image/svg+xml';
    case '.woff2': return 'font/woff2';
    case '.css': return 'text/css';
    case '.js': return 'application/javascript';
    default: return 'application/octet-stream';
  }
}

function serveEmbeddedAsset(pathname: string): Response | null {
  switch (pathname) {
    case '/':
    case '/index.html':
      if (indexHtml) {
        return new Response(indexHtml, {
          headers: { 'Content-Type': 'text/html' }
        });
      }
      break;

    case '/static/logo.svg':
      if (logoSvg) {
        return new Response(logoSvg, {
          headers: { 'Content-Type': 'image/svg+xml' }
        });
      }
      break;

    case '/static/founders-grotesk-bold.woff2':
      if (foundersGroteskFont) {
        return new Response(foundersGroteskFont, {
          headers: {
            'Content-Type': 'font/woff2',
            'Cache-Control': 'public, max-age=31536000'
          }
        });
      }
      break;

    case '/static/national-regular.woff2':
      if (nationalFont) {
        return new Response(nationalFont, {
          headers: {
            'Content-Type': 'font/woff2',
            'Cache-Control': 'public, max-age=31536000'
          }
        });
      }
      break;
  }

  return null;
}

async function serveStaticFile(filePath: string): Promise<Response> {
  try {
    const file = Bun.file(filePath);
    return new Response(file);
  } catch (error) {
    return new Response("Internal server error", { status: 500 });
  }
}

await loadAssets();

const PORT: number = 8888;

const server = Bun.serve({
  port: PORT,
  hostname: "0.0.0.0",
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const { pathname, method } = {
      pathname: url.pathname,
      method: request.method,
    };

    if (method === "GET") {
      // Try to serve embedded asset first
      const embeddedAsset = serveEmbeddedAsset(pathname);
      if (embeddedAsset) {
        return embeddedAsset;
      }

      // Fallback to file system for development mode
      if (pathname === "/" || pathname === "/index.html") {
        return serveStaticFile(path.join(__dirname, "static/index.html"));
      }

      if (pathname.startsWith("/static/")) {
        const assetPath = path.join(__dirname, pathname);
        return serveStaticFile(assetPath);
      }
    }

    if (method === "POST" && pathname === "/generate") {
      return handleGenerateWallet();
    }

    if (method === "POST" && pathname === "/save") {
      return handleSaveWallet(request);
    }

    if (method === "POST" && pathname === "/derive") {
      return handleDeriveWallet(request);
    }

    return new Response("Not Found", { status: 404 });
  },
});

console.log("octra wallet generator server");
console.log(`The server is running at: http://localhost:${PORT}`);
