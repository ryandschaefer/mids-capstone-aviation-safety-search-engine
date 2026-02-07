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