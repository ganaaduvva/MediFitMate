import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { z } from "zod";
import express, { Express } from "express";
import {
  getDrugByNDC,
  getHealthIndicators,
  searchDrugs,
  searchPubMedArticles,
  searchRxNormDrugs,
  searchGoogleScholar,
  getPubMedArticleByPMID,
  searchClinicalGuidelines,
  checkDrugInteractions,
  searchMedicalDatabases,
  searchMedicalJournals,
  createErrorResponse,
  formatDrugSearchResults,
  formatDrugDetails,
  formatHealthIndicators,
  formatPubMedArticles,
  formatGoogleScholarArticles,
  formatDrugInteractions,
  formatMedicalDatabasesSearch,
  formatMedicalJournalsSearch,
  formatArticleDetails,
  formatRxNormDrugs,
  formatClinicalGuidelines,
} from "./utils.js";

const server = new McpServer({
  name: "medical-mcp",
  version: "1.0.0",
  // capabilities: {
  //   resources: {},
  //   tools: {},
  // },
});


// MCP Tools
server.tool(
  "search-drugs",
  "Search for drug information using FDA database",
  {
    query: z
      .string()
      .describe("Drug name to search for (brand name or generic name)"),
    limit: z
      .number()
      .int()
      .min(1)
      .max(50)
      .optional()
      .default(10)
      .describe("Number of results to return (max 50)"),
  },
  async ({ query, limit }) => {
    try {
      const drugs = await searchDrugs(query, limit);
      return formatDrugSearchResults(drugs, query);
    } catch (error: any) {
      return createErrorResponse("searching drugs", error);
    }
  }
);

server.tool(
  "get-drug-details",
  "Get detailed information about a specific drug by NDC (National Drug Code)",
  {
    ndc: z.string().describe("National Drug Code (NDC) of the drug"),
  },
  async ({ ndc }) => {
    try {
      const drug = await getDrugByNDC(ndc);
      return formatDrugDetails(drug, ndc);
    } catch (error: any) {
      return createErrorResponse("fetching drug details", error);
    }
  }
);

server.tool(
  "get-health-statistics",
  "Get health statistics and indicators from WHO Global Health Observatory",
  {
    indicator: z
      .string()
      .describe(
        "Health indicator to search for (e.g., 'Life expectancy', 'Mortality rate')"
      ),
    country: z
      .string()
      .optional()
      .describe("Country code (e.g., 'USA', 'GBR') - optional"),
    limit: z
      .number()
      .int()
      .min(1)
      .max(20)
      .optional()
      .default(10)
      .describe("Number of results to return (max 20)"),
  },
  async ({ indicator, country, limit }) => {
    try {
      const indicators = await getHealthIndicators(indicator, country);
      return formatHealthIndicators(indicators, indicator, country, limit);
    } catch (error: any) {
      return createErrorResponse("fetching health statistics", error);
    }
  }
);

server.tool(
  "search-medical-literature",
  "Search for medical research articles in PubMed",
  {
    query: z.string().describe("Medical topic or condition to search for"),
    max_results: z
      .number()
      .int()
      .min(1)
      .max(20)
      .optional()
      .default(10)
      .describe("Maximum number of articles to return (max 20)"),
  },
  async ({ query, max_results }) => {
    try {
      const articles = await searchPubMedArticles(query, max_results);
      return formatPubMedArticles(articles, query);
    } catch (error: any) {
      return createErrorResponse("searching medical literature", error);
    }
  }
);

server.tool(
  "get-article-details",
  "Get detailed information about a specific medical article by PMID",
  {
    pmid: z.string().describe("PubMed ID (PMID) of the article"),
  },
  async ({ pmid }) => {
    try {
      const article = await getPubMedArticleByPMID(pmid);
      return formatArticleDetails(article, pmid);
    } catch (error: any) {
      return createErrorResponse("fetching article details", error);
    }
  }
);

server.tool(
  "search-drug-nomenclature",
  "Search for drug information using RxNorm (standardized drug nomenclature)",
  {
    query: z.string().describe("Drug name to search for in RxNorm database"),
  },
  async ({ query }) => {
    try {
      const drugs = await searchRxNormDrugs(query);
      return formatRxNormDrugs(drugs, query);
    } catch (error: any) {
      return createErrorResponse("searching RxNorm", error);
    }
  }
);

server.tool(
  "search-google-scholar",
  "Search for academic research articles using Google Scholar",
  {
    query: z
      .string()
      .describe("Academic topic or research query to search for"),
  },
  async ({ query }) => {
    try {
      const articles = await searchGoogleScholar(query);
      return formatGoogleScholarArticles(articles, query);
    } catch (error: any) {
      return createErrorResponse("searching Google Scholar", error);
    }
  }
);

server.tool(
  "search-clinical-guidelines",
  "Search for clinical guidelines and practice recommendations from medical organizations",
  {
    query: z
      .string()
      .describe("Medical condition or topic to search for guidelines"),
    organization: z
      .string()
      .optional()
      .describe(
        "Specific medical organization to filter by (e.g., 'American Heart Association', 'WHO')"
      ),
  },
  async ({ query, organization }) => {
    try {
      const guidelines = await searchClinicalGuidelines(query, organization);
      return formatClinicalGuidelines(guidelines, query, organization);
    } catch (error: any) {
      return createErrorResponse("searching clinical guidelines", error);
    }
  }
);

server.tool(
  "check-drug-interactions",
  "Check for potential drug-drug interactions between two medications",
  {
    drug1: z.string().describe("First drug name"),
    drug2: z.string().describe("Second drug name"),
  },
  async ({ drug1, drug2 }) => {
    try {
      const interactions = await checkDrugInteractions(drug1, drug2);
      return formatDrugInteractions(interactions, drug1, drug2);
    } catch (error: any) {
      return createErrorResponse("checking drug interactions", error);
    }
  }
);

// Enhanced Medical Database Search Tool
server.tool(
  "search-medical-databases",
  "Search across multiple medical databases (PubMed, Google Scholar, Cochrane, ClinicalTrials.gov) for comprehensive results",
  {
    query: z
      .string()
      .describe(
        "Medical topic or condition to search for across multiple databases"
      ),
  },
  async ({ query }) => {
    try {
      const articles = await searchMedicalDatabases(query);
      return formatMedicalDatabasesSearch(articles, query);
    } catch (error: any) {
      return createErrorResponse("searching medical databases", error);
    }
  }
);

// Enhanced Medical Journal Search Tool
server.tool(
  "search-medical-journals",
  "Search specific medical journals (NEJM, JAMA, Lancet, BMJ, Nature Medicine) for high-quality research",
  {
    query: z
      .string()
      .describe(
        "Medical topic or condition to search for in top medical journals"
      ),
  },
  async ({ query }) => {
    try {
      const articles = await searchMedicalJournals(query);
      return formatMedicalJournalsSearch(articles, query);
    } catch (error: any) {
      return createErrorResponse("searching medical journals", error);
    }
  }
);

async function main() {
  const app: Express = express();
  let transport:SSEServerTransport;
  const port = 8000;
  // Middleware
  app.use(express.json());

  // Health check endpoint
  app.get("/health", (req: any, res: any) => {
    res.json({ status: "healthy", transport: "sse" });
  });

  // Server info endpoint
  app.get("/info", (req: any, res: any) => {
    res.json({
      name: "medical-mcp",
      version: "1.0.0",
      transport: "sse",
      tools: [
        "search-drugs",
        "get-drug-details",
        "get-health-statistics",
        "search-medical-literature",
        "get-article-details",
        "search-drug-nomenclature",
        "search-google-scholar",
        "search-clinical-guidelines",
        "check-drug-interactions",
        "search-medical-databases",
        "search-medical-journals",
      ],
    });
  });

  // SSE endpoint for MCP
  app.get("/sse", async (req: any, res: any) => {
    console.info("📡 New SSE connection established");

    transport = new SSEServerTransport("/messages", res);
    server.connect(transport).catch((err: any) => {
      console.error("❌ SSE server error:", err);
    });

    // Keep alive with a ping every 15s (optional)
    const keepAlive = setInterval(() => {
      res.write(":\n\n");
    }, 15000);

    req.on("close", () => {
      clearInterval(keepAlive);
      console.error("📡 SSE connection closed");
    });
  });

  // POST endpoint for client messages
  app.post("/messages", async (req: any, res: any) => {
    // console.error("📨 Received message from client");
    // SSEServerTransport handles this internally
    await transport.handleMessage(req.body).catch((err: any) => {
      console.error("❌ Error handling client message:", err);
    });
    res.status(200).send();
  });

  // Start server
  app.listen(port, "0.0.0.0", () => {
    console.info(`✅ Medical MCP Server running on http://0.0.0.0:${port}`);
    console.info(`📡 SSE endpoint: http://0.0.0.0:${port}/sse`);
    console.info(`📨 Messages endpoint: http://0.0.0.0:${port}/messages`);
    console.info(`❤️  Health check: http://0.0.0.0:${port}/health`);
  });

  // Graceful shutdown
  process.on("SIGINT", () => {
    // console.error("\n🛑 Shutting down Medical MCP Server...");
    process.exit(0);
  });

}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
