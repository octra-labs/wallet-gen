#!/usr/bin/env bun
import { Command } from "commander";
import { registerKeyCommands } from "./commands/keys";

const program = new Command();

program
  .name("octra-wallet-cli")
  .description("A CLI tool with a local keystore for Octra wallets.")
  .version("1.0.0");

// Register commands
registerKeyCommands(program);

// Show help by default if no args
if (process.argv.length <= 2) {
  program.outputHelp();
} else {
  program.parseAsync(process.argv);
}
