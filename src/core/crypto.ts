import crypto from "crypto";
import nacl from "tweetnacl";
import { base58Encode } from "../utils/converters";
import { BASE58_ALPHABET, OCTRA_ADDRESS_PREFIX } from "../utils/constants";

export function generateEntropy(strength: number = 128): Buffer {
  if (![128, 160, 192, 224, 256].includes(strength)) {
    throw new Error("Strength must be 128, 160, 192, 224 or 256 bits");
  }
  return crypto.randomBytes(strength / 8);
}

export function createOctraAddress(publicKey: Buffer): string {
  const hash = crypto.createHash("sha256").update(publicKey).digest();
  const base58Hash = base58Encode(hash);
  return `${OCTRA_ADDRESS_PREFIX}${base58Hash}`;
}

export function verifyAddressFormat(address: string): boolean {
  if (!address.startsWith(OCTRA_ADDRESS_PREFIX)) return false;
  if (address.length !== 47) return false;

  const base58Part = address.slice(OCTRA_ADDRESS_PREFIX.length);
  for (const char of base58Part) {
    if (!BASE58_ALPHABET.includes(char)) return false;
  }

  return true;
}

export function sign(message: Buffer, secretKey: Uint8Array): Uint8Array {
  return nacl.sign.detached(message, secretKey);
}

export function verifySignature(
  message: Buffer,
  signature: Uint8Array,
  publicKey: Uint8Array
): boolean {
  return nacl.sign.detached.verify(message, signature, publicKey);
}
