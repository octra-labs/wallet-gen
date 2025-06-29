import { RPC_URL } from "../utils/constants";

interface BalanceResponse {
  balance: string;
  nonce: number;
}

export interface BalanceData {
  amount: string;
  denom: string;
}

/**
 * Handles all communication with the Octra network RPC endpoints.
 */
export class NetworkService {
  /**
   * Fetches the balance for a given Octra address.
   * @param {string} address - The Octra address to query.
   * @returns {Promise<BalanceData>} A promise that resolves to the account's balance data.
   */
  public async getBalance(address: string): Promise<BalanceData> {
    try {
      const response = await fetch(`${RPC_URL}/balance/${address}`);

      if (!response.ok) {
        if (response.status === 403) {
          try {
            const errorData = await response.json();
            if (errorData && errorData.error === "Sender not found") {
              return { amount: "0.000000", denom: "oct" };
            }
          } catch (e) {
            throw new Error(
              `Network request failed with status: 403 (unreadable error body)`
            );
          }
        }
        
        throw new Error(
          `Network request failed with status: ${response.status}`
        );
      }

      const data: BalanceResponse = await response.json();

      const amountAsNumber = parseFloat(data.balance);
      return {
        amount: amountAsNumber.toFixed(6),
        denom: "oct",
      };
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to fetch balance: ${error.message}`);
      }
      throw new Error("An unknown network error occurred.");
    }
  }
}
