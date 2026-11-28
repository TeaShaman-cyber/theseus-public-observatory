import { DuckDB, init, version } from "@ducklings/workers";
import wasmModule from "./duckdb-workers.wasm";
import queries from "./queries.json";

export default {
  async fetch(request) {
    const { sources, samples } = await request.json();
    await init({ wasmModule });
    const db = new DuckDB({ customConfig: { threads: "1", memory_limit: "48MB" } });
    const conn = db.connect();
    try {
      for (const [name, bytes] of Object.entries({ sources, samples })) {
        await db.registerFileBuffer(name + ".parquet", Uint8Array.from(bytes));
        await conn.execute("CREATE VIEW " + name + " AS SELECT * FROM read_parquet('" + name + ".parquet')");
      }
      const results = {};
      for (const [name, sql] of Object.entries(queries)) results[name] = await conn.query(sql);
      return Response.json({ version: version(), results }, {
        headers: { "content-type": "application/json" },
      });
    } finally {
      conn.close();
      db.close();
    }
  }
};
