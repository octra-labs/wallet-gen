import * as bip39 from "bip39";
import nacl from "tweetnacl";
import type { WalletData } from "../types/wallet";
import * as crypto from "../core/crypto";
import * as hdWallet from "../core/hd-wallet";
import { bufferToHex, base64Encode } from "../utils/converters";

const OCTRA_BIP44_PATH = {
  purpose: 44,
  coinType: 345,
  account: 0,
  change: 0,
};

export class CliWalletService {
  /**
   * Generates a brand new wallet from fresh entropy.
   * @param {number} [index=0] - The address index to derive.
   * @returns {WalletData} The full wallet data object.
   */
  public generateNewKey(index: number = 0): WalletData {
    const mnemonic = bip39.generateMnemonic(256);
    const mnemonicWords = mnemonic.split(" ");

    const seed = bip39.mnemonicToSeedSync(mnemonic);

    const path = [
      (OCTRA_BIP44_PATH.purpose | 0x80000000) >>> 0,
      (OCTRA_BIP44_PATH.coinType | 0x80000000) >>> 0,
      (OCTRA_BIP44_PATH.account | 0x80000000) >>> 0,
      OCTRA_BIP44_PATH.change,
      index,
    ];

    const { key: derivedKey, chain: derivedChain } = hdWallet.derivePath(
      seed,
      path
    );
    const keyPair = nacl.sign.keyPair.fromSeed(derivedKey);
    const privateKeyRaw = Buffer.from(keyPair.secretKey.slice(0, 32));
    const publicKeyRaw = Buffer.from(keyPair.publicKey);

    const address = crypto.createOctraAddress(publicKeyRaw);

    return {
      mnemonic: mnemonicWords,
      address,
      private_key_hex: bufferToHex(privateKeyRaw),
      public_key_hex: bufferToHex(publicKeyRaw),
      private_key_b64: base64Encode(privateKeyRaw),
      public_key_b64: base64Encode(publicKeyRaw),
      seed_hex: bufferToHex(seed),
      master_chain_hex: bufferToHex(derivedChain),
      entropy_hex: bip39.mnemonicToEntropy(mnemonic),
      test_message: "",
      test_signature: "",
      signature_valid: false,
    };
  }
}
