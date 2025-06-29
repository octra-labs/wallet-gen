import { Command } from "commander";
import { KeyStoreService } from "../services/keystore.service";
import { NetworkService } from "../services/network.service";
import { OCTRA_ADDRESS_PREFIX } from "../utils/constants";

const keyStoreService = new KeyStoreService();
const networkService = new NetworkService();

const isAddress = (str: string): boolean => {
  return str.startsWith(OCTRA_ADDRESS_PREFIX) && str.length > 40;
};

export function registerQueryCommands(program: Command) {
  const queryCommand = program
    .command("query")
    .alias("q")
    .description("Query blockchain data, such as balances");

  queryCommand
    .command("balance")
    .alias("b")
    .description("Get the balance of a saved key or any Octra address")
    .argument(
      "[name_or_address]",
      "The name of the key in the keystore or a raw Octra address"
    )
    .action(handleGetBalance);
}

async function handleGetBalance(nameOrAddress?: string) {
  if (!nameOrAddress) {
    console.error(
      "Error: missing key name or address (must provide key name or valid address)"
    );
    process.exit(1);
  }

  try {
    let address: string;
    let displayName = nameOrAddress;

    if (isAddress(nameOrAddress)) {
      address = nameOrAddress;
    } else {
      const key = await keyStoreService.showKey(nameOrAddress);
      address = key.address;
    }

    const balanceData = await networkService.getBalance(address);

    console.log(`\nBalance for ${displayName} (${address}):`);
    console.log(`- amount: "${balanceData.amount}"`);
    console.log(`  denom: "${balanceData.denom}"`);
  } catch (error) {
    const message = error instanceof Error ? error.message : "unexpected error";

    if (message.includes("not found in keystore")) {
      console.error(`Error: key not found: '${nameOrAddress}'`);
    } else {
      console.error(`Error: ${message}`);
    }

    process.exit(1);
  }
}
