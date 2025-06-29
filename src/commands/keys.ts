import { Command } from "commander";
import { CliWalletService } from "../services/cli-wallet.service";
import { KeyStoreService } from "../services/keystore.service";

const cliWalletService = new CliWalletService();
const keyStoreService = new KeyStoreService();
const DEFAULT_INDEX = "0";

export function registerKeyCommands(program: Command) {
  const keysCommand = program.command("keys").description("Manage local keys");

  keysCommand
    .command("add")
    .description("Create and save a new key to the local keystore")
    .argument("<name>", "Key name (e.g., my-wallet, validator)")
    .option("--index <number>", "HD derivation index", DEFAULT_INDEX)
    .action(handleAddKey);

  keysCommand
    .command("list")
    .alias("ls")
    .description("List all keys stored locally")
    .action(handleListKeys);

  keysCommand
    .command("show")
    .description("Display full information about a stored key")
    .argument("<name>", "Key name to show")
    .action(handleShowKey);
}

async function handleAddKey(name: string, options: { index: string }) {
  const index = parseInt(options.index, 10);

  try {
    console.log(`\nCreating new key: ${name}`);
    const wallet = cliWalletService.generateNewKey(index);
    await keyStoreService.saveKey(name, wallet);

    console.log("\nKey created and saved successfully.");
    console.log("-".repeat(80));
    console.log(`  Name     : ${name}`);
    console.log(`  Address  : ${wallet.address}`);
    console.log("\nThe mnemonic is stored in your keystore file.");
    console.log("Make sure to keep it safe and backed up securely.");
    console.log("-".repeat(80));
  } catch (error) {
    logError("Failed to create and save key", error);
  }
}

async function handleListKeys() {
  try {
    const keys = await keyStoreService.listKeys();

    if (keys.length === 0) {
      console.log("No keys found. Use 'keys add <name>' to create one.");
      return;
    }

    keys.forEach((key, idx) => {
      console.log(`- name     : ${key.name}`);
      console.log(`  type     : local`);
      console.log(`  address  : ${key.address}`);
      console.log(`  pubkey   : ${key.pubkey}`);
      if (idx < keys.length - 1) console.log("");
    });
  } catch (error) {
    logError("Failed to list keys", error);
  }
}

async function handleShowKey(name: string) {
  try {
    const keyData = await keyStoreService.showKey(name);

    console.log(`\nKey: ${name}`);
    console.log("-".repeat(80));
    console.log(`  Address   : ${keyData.address}`);
    console.log(`  PublicKey : ${keyData.publicKey}`);
    console.log(`  Mnemonic  : ${keyData.mnemonic}`);
    console.log("\nNote: This information is sensitive. Handle with care.");
    console.log("-".repeat(80));
  } catch (error) {
    logError("Failed to display key details", error);
  }
}

function logError(context: string, error: unknown) {
  const message =
    error instanceof Error ? error.message : "An unexpected error occurred.";
  console.error(`\n[ERROR] ${context}: ${message}`);
  process.exit(1);
}
