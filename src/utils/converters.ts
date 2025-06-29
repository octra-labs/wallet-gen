import { BASE58_ALPHABET } from "./constants";

export function bufferToHex(buffer: Buffer | Uint8Array): string {
  return Buffer.from(buffer).toString("hex");
}

export function hexToBuffer(hex: string): Buffer {
  return Buffer.from(hex, "hex");
}

export function base64Encode(buffer: Buffer | Uint8Array): string {
  return Buffer.from(buffer).toString("base64");
}

export function base58Encode(buffer: Buffer): string {
  if (buffer.length === 0) return "";

  let num = BigInt("0x" + buffer.toString("hex"));
  let encoded = "";

  while (num > 0n) {
    const remainder = num % 58n;
    num = num / 58n;
    encoded = BASE58_ALPHABET[Number(remainder)] + encoded;
  }

  for (let i = 0; i < buffer.length && buffer[i] === 0; i++) {
    encoded = "1" + encoded;
  }

  return encoded;
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
