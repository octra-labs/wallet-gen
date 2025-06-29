import fs from "fs/promises";
import path from "path";
import os from "os";
import type { WalletData } from "../types/wallet";

const KEYSTORE_DIR = path.join(os.homedir(), ".octra-keys");

interface StoredKey {
  name: string;
  address: string;
  publicKey: string;
  privateKey: string;
  mnemonic: string;
  createdAt: string;
}

interface KeySummary {
  name: string;
  address: string;
  pubkey: string;
}

export class KeyStoreService {
  private async ensureKeystoreDir(): Promise<void> {
    try {
      await fs.access(KEYSTORE_DIR);
    } catch {
      await fs.mkdir(KEYSTORE_DIR, { recursive: true });
    }
  }

  public async saveKey(keyName: string, walletData: WalletData): Promise<void> {
    await this.ensureKeystoreDir();
    const filePath = this.getKeyFilePath(keyName);

    try {
      await fs.access(filePath);
      throw new Error(`Key '${keyName}' already exists in keystore.`);
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== "ENOENT") {
        throw err;
      }
    }

    const keyToStore: StoredKey = {
      name: keyName,
      address: walletData.address,
      publicKey: walletData.public_key_b64,
      privateKey: walletData.private_key_b64,
      mnemonic: walletData.mnemonic.join(" "),
      createdAt: new Date().toISOString(),
    };

    await fs.writeFile(filePath, JSON.stringify(keyToStore, null, 2));
  }

  public async listKeys(): Promise<KeySummary[]> {
    await this.ensureKeystoreDir();
    const files = await fs.readdir(KEYSTORE_DIR);

    const summaries: KeySummary[] = [];
    for (const file of files) {
      if (!file.endsWith(".json")) continue;

      const filePath = path.join(KEYSTORE_DIR, file);
      const content = await fs.readFile(filePath, "utf-8");

      try {
        const key: StoredKey = JSON.parse(content);
        summaries.push({
          name: key.name,
          address: key.address,
          pubkey: key.publicKey,
        });
      } catch {
        continue; // Skip malformed files
      }
    }

    return summaries;
  }

  public async showKey(keyName: string): Promise<StoredKey> {
    await this.ensureKeystoreDir();
    const filePath = this.getKeyFilePath(keyName);

    try {
      const content = await fs.readFile(filePath, "utf-8");
      return JSON.parse(content) as StoredKey;
    } catch {
      throw new Error(`Key '${keyName}' not found in keystore.`);
    }
  }

  private getKeyFilePath(keyName: string): string {
    return path.join(KEYSTORE_DIR, `${keyName}.json`);
  }
}
