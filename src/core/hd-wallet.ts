import crypto from "crypto";
import nacl from "tweetnacl";
import type { MasterKey, ChildKey, DerivedPath } from "../types/wallet.ts";

export function deriveMasterKey(seed: Buffer): MasterKey {
  const key = Buffer.from("Octra seed", "utf8");
  const mac = crypto.createHmac("sha512", key).update(seed).digest();

  const masterPrivateKey = mac.slice(0, 32);
  const masterChainCode = mac.slice(32, 64);

  return { masterPrivateKey, masterChainCode };
}

export function deriveChildKeyEd25519(
  privateKey: Buffer,
  chainCode: Buffer,
  index: number
): ChildKey {
  const data = Buffer.alloc(1 + 32 + 4);

  if (index >= 0x80000000) {
    // Hardened derivation
    data[0] = 0x00;
    privateKey.copy(data, 1);
    data.writeUInt32BE(index, 33);
  } else {
    // Non-hardened derivation
    const keyPair = nacl.sign.keyPair.fromSeed(privateKey);
    const publicKey = Buffer.from(keyPair.publicKey);
    publicKey.copy(data, 0);
    data.writeUInt32BE(index, 32);
  }

  const mac = crypto.createHmac("sha512", chainCode).update(data).digest();
  const childPrivateKey = mac.slice(0, 32);
  const childChainCode = mac.slice(32, 64);

  return { childPrivateKey, childChainCode };
}

export function derivePath(seed: Buffer, path: number[]): DerivedPath {
  const { masterPrivateKey, masterChainCode } = deriveMasterKey(seed);
  let key = masterPrivateKey;
  let chain = masterChainCode;

  for (const index of path) {
    const derived = deriveChildKeyEd25519(key, chain, index);
    key = derived.childPrivateKey;
    chain = derived.childChainCode;
  }

  return { key, chain };
}
