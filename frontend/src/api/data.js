import { BASE_ENDPOINT } from "./utils";
import axios from "axios";

const GROUP_ENDPOINT = `${ BASE_ENDPOINT }/data`;

export const getTestData = async() => {
    const endpoint = `${ GROUP_ENDPOINT }/test`;
    // Send API call
    const res = await axios.get(endpoint);

    // Handle error
    if (res.status !== 200) {
        console.error(`API request "GET ${ endpoint }" failed with status code ${ res.status }`);
        throw new Error(res.statusText);
    }

    return res.data;
}

export const getBM25Data = async(query) => {
    const endpoint = `${ GROUP_ENDPOINT }/bm25`;
    // Configure query parameters
    const config = {
        params: {
            query
        }
    }
    // Send API call
    const res = await axios.get(endpoint, config);

    // Handle error
    if (res.status !== 200) {
        console.error(`API request "GET ${ endpoint }" failed with status code ${ res.status }`);
        throw new Error(res.statusText);
    }

    return res.data;
}

export const getSemanticData = async(query, expand = true) => {
    const endpoint = `${ GROUP_ENDPOINT }/semantic`;
    const config = {
        params: { query, expand }
    }
    const res = await axios.get(endpoint, config);

    if (res.status !== 200) {
        console.error(`API request "GET ${ endpoint }" failed with status code ${ res.status }`);
        throw new Error(res.statusText);
    }

    return res.data;
}

export const getHybridData = async(query, expand = true, alpha = null) => {
    const endpoint = `${ GROUP_ENDPOINT }/hybrid`;
    const config = {
        params: { query, expand, ...(alpha !== null && { alpha }) }
    }
    const res = await axios.get(endpoint, config);

    if (res.status !== 200) {
        console.error(`API request "GET ${ endpoint }" failed with status code ${ res.status }`);
        throw new Error(res.statusText);
    }

    return res.data;
}