#!/usr/bin/env node
import { readFile } from "node:fs/promises";
import { validateJurisdictionReceiptSchema } from "../vendor/assay-verify.mjs";

function fieldLabel(issue) {
  return issue.field ? `${issue.field}: ${issue.message}` : issue.message;
}

function emitError(file, message) {
  console.error(`::error file=${file},title=Invalid Guardian jurisdiction receipt::${message}`);
}

async function validateFile(file) {
  let receipt;
  try {
    receipt = JSON.parse(await readFile(file, "utf8"));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    emitError(file, `Cannot read or parse JSON: ${message}`);
    return false;
  }

  const issues = validateJurisdictionReceiptSchema(receipt);
  if (issues.length === 0) {
    console.log(`ok: jurisdiction receipt valid: ${file}`);
    return true;
  }

  for (const issue of issues) {
    emitError(file, `${file}: ${fieldLabel(issue)}`);
  }
  return false;
}

async function main() {
  const files = process.argv.slice(2);
  if (files.length === 0) {
    console.error("usage: validate-jurisdiction-receipts.mjs <receipt.json> [...]");
    process.exitCode = 2;
    return;
  }

  let ok = true;
  for (const file of files) {
    ok = (await validateFile(file)) && ok;
  }
  process.exitCode = ok ? 0 : 2;
}

await main();
