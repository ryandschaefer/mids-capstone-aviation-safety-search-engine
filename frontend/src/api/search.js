import { BASE_ENDPOINT } from "./utils";
import axios from "axios";

const SEARCH_ENDPOINT = `${BASE_ENDPOINT}/search`;

export const getTestData = async () => {
    const res = await axios.get(`${SEARCH_ENDPOINT}/test`);
    if (res.status !== 200) {
        console.error(`API request failed with status ${res.status}`);
        throw new Error(res.statusText);
    }
    return res.data;
};

/**
 * Call Ryan's POST /search (main_driver). Returns the results array for the UI.
 * @param {string} query - Search query
 * @param {string} mode - "bm25" | "embeddings" | "hybrid"
 * @param {number} top_k - Max results to return (default 50)
 */
export const getSearchResults = async (query, mode = "bm25", top_k = 50) => {
    const res = await axios.post(SEARCH_ENDPOINT, { query, mode, top_k });
    if (res.status !== 200) {
        console.error(`POST ${SEARCH_ENDPOINT} failed with status ${res.status}`);
        throw new Error(res.statusText);
    }
    return res.data.data;
};

/** @deprecated use getSearchResults */
export const startSearch = async (query, mode = "bm25") => {
    const res = await axios.post(SEARCH_ENDPOINT, { query, mode, top_k: 50 });
    if (res.status !== 200) throw new Error(res.statusText);
    return res.data;
};