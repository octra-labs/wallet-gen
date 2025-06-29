export interface MasterKey {
  masterPrivateKey: Buffer;
  masterChainCode: Buffer;
}

export interface ChildKey {
  childPrivateKey: Buffer;
  childChainCode: Buffer;
}

export interface DerivedPath {
  key: Buffer;
  chain: Buffer;
}

export interface NetworkDerivation {
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

export interface WalletData {
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

export interface DeriveRequest {
  seed_hex: string;
  network_type?: number;
  index?: number;
}
