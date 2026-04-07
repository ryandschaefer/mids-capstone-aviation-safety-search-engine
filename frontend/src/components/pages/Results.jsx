import { DataTable } from "primereact/datatable";
import { Column } from "primereact/column";
import { FilterMatchMode, FilterOperator, PrimeReactProvider } from "primereact/api";
import "primereact/resources/themes/lara-light-indigo/theme.css";
import { useEffect, useState, useMemo } from "react";
import { Box, Button, Chip, FormControl, FormControlLabel, Grid, IconButton, InputLabel, MenuItem, Select, Switch, Tooltip, Typography } from "@mui/material";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import ThumbUpAltOutlinedIcon from "@mui/icons-material/ThumbUpAltOutlined";
import ThumbDownAltOutlinedIcon from "@mui/icons-material/ThumbDownAltOutlined";
import { allColumns, SearchBar } from "../common";
import { createSearch, getSearchResults, downloadSearchResults } from "../../api";
import { useNavigate } from "react-router-dom";
import humanizeDuration from "humanize-duration";
import { MultiSelect } from "primereact/multiselect";

const primeReactConfig = {
    hideOverlaysOnDocumentScrolling: false
};

const SEARCH_MODE_KEY = "search-mode";
const FEEDBACK_KEY = "result-feedback-v1";
const USE_QE_KEY = "use-qe";
const USE_QE_JUDGE_KEY = "use-qe-judge";
const USE_FEEDBACK_1 = "use-feedback-1";

const HighlightText = ({ narrative, chunks = [] }) => {
    if (!chunks.length || !narrative) return <span>{narrative}</span>;

    // Build and sort match ranges
    const ranges = chunks
        .map((chunk) => {
            const index = chunk ? narrative.toLowerCase().indexOf(chunk.toLowerCase()) : -1;
            return index === -1 ? null : { start: index, end: index + chunk.length };
            })
        .filter(Boolean)
        .sort((a, b) => a.start - b.start);

    if (!ranges.length) return <span>{narrative}</span>;

    // Build output segments
    const segments = [];
    let cursor = 0;
    ranges.forEach(({ start, end }, i) => {
        if (cursor < start) segments.push(<span key={`t-${i}`}>{narrative.slice(cursor, start)}</span>);
        segments.push(<mark style={{ background: "#FAC775", color: "#412402", borderRadius: 3, padding: "0 2px" }} key={`b-${i}`}>{narrative.slice(start, end)}</mark>);
        cursor = end;
    });
    if (cursor < narrative.length) segments.push(<span key="tail">{narrative.slice(cursor)}</span>);

    return <span>{segments}</span>;
}

export const Results = () => {
    const navigate = useNavigate();

    const [loading, setLoading] = useState(false);
    const [searchResults, setSearchResults] = useState([]);
    const [totalResults, setTotalResults] = useState(-1);
    const [currentPage, setCurrentPage] = useState(0);
    const [pageLength, setPageLength] = useState(10);
    const [userQuery, setUserQuery] = useState("");
    const [searchMode, setSearchMode] = useState(localStorage.getItem(SEARCH_MODE_KEY) || "bm25");
    const [useQe, setUseQe] = useState(localStorage.getItem(USE_QE_KEY) === "true");
    const [useQeJudge, setUseQeJudge] = useState(localStorage.getItem(USE_QE_JUDGE_KEY) === "true");
    const [useFeedback1, setUseFeedback1] = useState(localStorage.getItem(USE_FEEDBACK_1) === "true");
    const [queryTime, setQueryTime] = useState(-1.0);
    const [queryTimeText, setQueryTimeText] = useState("");
    const [expandedQuery, setExpandedQuery] = useState("");
    const [cacheKey, setCacheKey] = useState("");
    const [isCached, setIsCached] = useState(false);
    const [disableFileDownload, setDisableFileDownload] = useState(false);
    const [metadataFilters, setMetadataFilters] = useState({});
    const [visibleColumns, setVisibleColumns] = useState([
        "acn_num_ACN", "Time_Date", "Time.1_Local Time Of Day", "Place_Locale Reference"
    ]);
    const [feedbackByDoc, setFeedbackByDoc] = useState(() => {
        try {
            return JSON.parse(localStorage.getItem(FEEDBACK_KEY) || "{}");
        } catch {
            return {};
        }
    });

    const onSubmit = () => {
        const query = localStorage.getItem("user-query");
        if (query) {
            setLoading(true);
            const topK = useFeedback1 ? 500 : 50;

            createSearch(query, searchMode, topK, {
                use_qe: useQe,
                use_qe_judge: useQeJudge,
                use_feedback_1: useFeedback1
            })
                .then(response => {
                    // Reset metadata filters for new query
                    initMetadataFilters();
                    // Save search metadata
                    setCacheKey(response.cache_key);
                    setIsCached(response.cached);
                    setTotalResults(response.total_results);
                    // Save expanded query
                    const used = Array.isArray(response?.used_queries) ? response.used_queries : [];
                    const latestUsedQuery = used.length > 0 ? String(used[used.length - 1]) : "";
                    const isExpanded =
                        latestUsedQuery &&
                        latestUsedQuery.trim().toLowerCase() !== query.trim().toLowerCase();
                    setExpandedQuery(isExpanded ? latestUsedQuery : "");
                    // Save search time
                    if (response?.times?.api_total) {
                        setQueryTime(response.times.api_total * 1000);
                    }

                    // Load the first page of results for the new search
                    if (currentPage === 0) {
                        getPage(response.cache_key, 0, pageLength);
                    } else {
                        setCurrentPage(0);
                    }
                })
                .catch(err => {
                    console.log(err);
                    setLoading(false);
                })
                .finally(() => {
                    setUserQuery(query);
                })
            
        } else {
            navigate("/");
        }
    };

    const getPage = (cacheKey, currentPage, pageLength) => {
        if (cacheKey) {
            setLoading(true);
            getSearchResults(cacheKey, currentPage, pageLength, metadataFilters)
                .then((response) => {
                    const rows = Array.isArray(response?.data) ? response.data : [];
                    setSearchResults(rows);
                    setTotalResults(response.total_results);
                })
                .finally(() => {
                    setLoading(false);
                });
        }
    }

    const onPage = (event) => {
        setCurrentPage(event.page);
    };

    const setDocFeedback = (docId, value) => {
        if (!docId) return;
        setFeedbackByDoc((prev) => {
            const next = { ...prev, [docId]: value };
            localStorage.setItem(FEEDBACK_KEY, JSON.stringify(next));
            return next;
        });
    };

    const getDocId = (record) => String(record.doc_id ?? record.acn_num_ACN ?? "");

    const onToggleQe = (checked) => {
        setUseQe(checked);
        localStorage.setItem(USE_QE_KEY, String(checked));
        if (!checked) {
            // Judge mode depends on query enhancement path.
            setUseQeJudge(false);
            localStorage.setItem(USE_QE_JUDGE_KEY, "false");
        }
    };

    const initMetadataFilters = () => {
        const _filters = { submit_filters: false };

        allColumns.forEach(col => {
            _filters[col.value] = {
                operator: FilterOperator.AND,
                constraints: [{
                    value: null,
                    matchMode: FilterMatchMode.EQUALS
                }],
                maxConstraints: Infinity
            }
        });

        setMetadataFilters(_filters);
    }

    const applyMetadataFilters = (event) => {
        setMetadataFilters({
            ...event.filters,
            submit_filters: true
        })
    }

    const renderTableColumns = useMemo(() => (
            visibleColumns.map((col, i) => {
                const column = allColumns.filter(x => x.value === col)[0];
                if (column) {
                    const id = column.value;
                    const colName = column.label;

                    return (
                        <Column
                            key={i}
                            field={id}
                            header={colName}
                            style={{ minWidth: "130px", wordWrap: "break-word" }}
                            body={(record) => (
                                <Box
                                    sx={{
                                        minHeight: "60px",
                                        maxHeight: "200px",
                                        overflowY: "auto",
                                        verticalAlign: "top",
                                        pt: 0.5,
                                        whiteSpace: "normal",
                                        wordWrap: "break-word",
                                        lineHeight: 1.4,
                                        fontSize: "0.875rem",
                                        "&::-webkit-scrollbar": { width: "6px" },
                                        "&::-webkit-scrollbar-track": { background: "#f1f1f1", borderRadius: "3px" },
                                        "&::-webkit-scrollbar-thumb": { background: "#c1c1c1", borderRadius: "3px" },
                                        "&::-webkit-scrollbar-thumb:hover": { background: "#a1a1a1" },
                                    }}
                                >
                                    {record[id]}
                                </Box>
                            )}
                            // Handle metadata filtering
                            filter
                            maxConstraints={Infinity}
                        />
                    );
                } else {
                    return <></>;
                }
            })
    ), [visibleColumns]);

    useEffect(() => {
        onSubmit();
    }, []);

    useEffect(() => {
        setQueryTimeText(
            humanizeDuration(queryTime, { round: true, units: ["s", "ms"] })
        );
    }, [queryTime]);

    useEffect(() => {
        getPage(cacheKey, currentPage, pageLength);
    }, [currentPage, pageLength]);

    useEffect(() => {
        if (metadataFilters.submit_filters) {
            // Load the first page of results for the new search
            if (currentPage === 0) {
                getPage(cacheKey, 0, pageLength);
            } else {
                setCurrentPage(0);
            }
        }
    }, [metadataFilters]);

    const onColumnToggle = (event) => {
        const selectedColumns = event.value;
        const orderedSelectedColumns = allColumns
            .filter((col) => selectedColumns.some((sCol) => sCol === col.value))
            .map(col => col.value);

        setVisibleColumns(orderedSelectedColumns);
    }

    const selectColumnsMenu = <MultiSelect
        value={visibleColumns}
        options={allColumns}
        optionLabel="label"
        onChange={onColumnToggle}
        display="chip"
    />

    return (
        <PrimeReactProvider value={primeReactConfig}>
            <Box sx={{ display: "flex", flexDirection: "column", textAlign: "center" }}>
                <Grid container rowSpacing={3} sx={{ mt: "5dvh" }}>
                    <Grid size={1}>
                        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", justifyContent: "center" }}>
                            <Button onClick={() => navigate("/")}>Home</Button>
                            <Button onClick={() => navigate("/about")}>About</Button>
                        </Box>
                    </Grid>

                    <Grid size={8}>
                        <Box sx={{ width: "80%", alignItems: "center", ml: "10%" }}>
                            <SearchBar
                                disabled={loading}
                                onSubmit={onSubmit}
                                initQuery={userQuery}
                            />
                        </Box>
                    </Grid>

                    <Grid size={3}>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                            <FormControl size="small" sx={{ minWidth: 100 }}>
                                <InputLabel>Mode</InputLabel>
                                <Select
                                    value={searchMode}
                                    label="Mode"
                                    onChange={(e) => {
                                        const mode = e.target.value;
                                        setSearchMode(mode);
                                        localStorage.setItem(SEARCH_MODE_KEY, mode);
                                    }}
                                    disabled={loading}
                                >
                                    <MenuItem value="bm25">Quick Search (BM25)</MenuItem>
                                    <MenuItem value="embeddings">Concept Search (Embeddings)</MenuItem>
                                    <MenuItem value="hybrid">Deeper Search (Hybrid)</MenuItem>
                                </Select>
                            </FormControl>
                            <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", mr: 1 }}>
                                <FormControlLabel
                                    control={
                                        <Switch
                                            size="small"
                                            checked={useQe}
                                            onChange={(e) => onToggleQe(e.target.checked)}
                                            disabled={loading}
                                        />
                                    }
                                    label="LLM Query Enhancement"
                                />
                                <FormControlLabel
                                    control={
                                        <Switch
                                            size="small"
                                            checked={useQeJudge}
                                            onChange={(e) => {
                                                const checked = e.target.checked;
                                                setUseQeJudge(checked);
                                                localStorage.setItem(USE_QE_JUDGE_KEY, String(checked));
                                            }}
                                            disabled={loading || !useQe}
                                        />
                                    }
                                    label="LLM Relevance Judge"
                                />
                                <FormControlLabel
                                    control={
                                        <Switch
                                            size="small"
                                            checked={useFeedback1}
                                            onChange={(e) => {
                                                const checked = e.target.checked;
                                                setUseFeedback1(checked);
                                                localStorage.setItem(USE_FEEDBACK_1, String(checked));
                                            }}
                                            disabled={loading}
                                        />
                                    }
                                    label="LLM Feedback Loop"
                                />
                            </Box>
                            {/* <MetadataFilters
                                disabled={loading}
                                filters={filters}
                                onFiltersChange={setFilters}
                                onApply={() => {}}
                            /> */}
                        </Box>
                    </Grid>

                    <Grid size={12}>
                        {loading && (
                            <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", mt: { xs: 3, sm: "50px" }, width: "100%" }}>
                                <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
                                    <div className="spinner-border" style={{ width: "5rem", height: "5rem" }} role="status">
                                        <span className="sr-only"></span>
                                    </div>
                                </div>
                            </Box>
                        )}

                        {!loading && (
                            <Box>
                                <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 1, mb: 1 }}>
                                    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.5 }}>
                                        <Typography variant="body1">
                                            {totalResults >= 0
                                                ? totalResults === 0
                                                    ? `No results for "${userQuery}". Try different keywords or clear filters.`
                                                    : `${totalResults} result${totalResults !== 1 ? "s" : ""} for "${userQuery}" in ${queryTimeText}`
                                                : ""}
                                        </Typography>
                                        {expandedQuery ? (
                                            <Typography variant="body2" color="text.secondary">
                                                Expanded query used: "{expandedQuery}"
                                            </Typography>
                                        ) : null}
                                        <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap" }}>
                                            <Chip size="small" label={`Mode: ${searchMode.toUpperCase()}`} />
                                            <Chip size="small" color={useQe ? "primary" : "default"} label={`Search Path: ${useQe ? "LLM Enhanced" : "Fast Baseline"}`} />
                                            <Chip size="small" color={useQe ? "primary" : "default"} label={`LLM QE: ${useQe ? "On" : "Off"}`} />
                                            <Chip size="small" color={useQeJudge ? "primary" : "default"} label={`LLM Judge: ${useQeJudge ? "On" : "Off"}`} />
                                            <Chip size="small" color={useFeedback1 ? "primary" : "default"} label={`LLM Feedback: ${useFeedback1 ? "On" : "Off"}`} />
                                        </Box>
                                    </Box>

                                    <div>
                                        {disableFileDownload === true && (
                                            <div className="spinner-border" style={{ width: "1rem", height: "1rem" }} role="status">
                                                <span className="sr-only"></span>
                                            </div>
                                        )}
                                        {totalResults > 0 && (
                                            <Button
                                                size="small"
                                                variant="outlined"
                                                startIcon={<FileDownloadIcon />}
                                                disabled={disableFileDownload}
                                                onClick={() => {
                                                    setDisableFileDownload(true);
                                                    downloadSearchResults(cacheKey, metadataFilters)
                                                        .finally(() => setDisableFileDownload(false));
                                                }}
                                            >
                                                Export CSV
                                            </Button>
                                        )}
                                    </div>
                                </Box>
                                <DataTable
                                    value={searchResults}
                                    scrollable
                                    showBoxlines
                                    stripedRows
                                    header={selectColumnsMenu}
                                    style={{ width: "100%", maxWidth: "100%" }}
                                    lazy
                                    paginator
                                    rows={pageLength}
                                    totalRecords={totalResults}
                                    onPage={onPage}
                                    first={currentPage * pageLength}
                                    emptyMessage="No Records Found"
                                    paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
                                    currentPageReportTemplate="Showing {first} to {last} of {totalRecords} entries"
                                    filters={metadataFilters}
                                    onFilter={applyMetadataFilters}
                                >
                                    { renderTableColumns }

                                    <Column
                                        key="Report 1_Narrative"
                                        field="Report 1_Narrative"
                                        header="Narrative"
                                        style={{ minWidth: "130px", wordWrap: "break-word" }}
                                        body={(record) => (
                                            <Box
                                                sx={{
                                                    minHeight: "60px",
                                                    maxHeight: "200px",
                                                    overflowY: "auto",
                                                    verticalAlign: "top",
                                                    pt: 0.5,
                                                    whiteSpace: "normal",
                                                    wordWrap: "break-word",
                                                    lineHeight: 1.4,
                                                    fontSize: "0.875rem",
                                                    "&::-webkit-scrollbar": { width: "6px" },
                                                    "&::-webkit-scrollbar-track": { background: "#f1f1f1", borderRadius: "3px" },
                                                    "&::-webkit-scrollbar-thumb": { background: "#c1c1c1", borderRadius: "3px" },
                                                    "&::-webkit-scrollbar-thumb:hover": { background: "#a1a1a1" },
                                                }}
                                            >
                                                <HighlightText
                                                    narrative={record["Report 1_Narrative"]}
                                                    chunks={record["chunks"]}
                                                />
                                            </Box>
                                        )}
                                    />

                                    <Column
                                        key="score"
                                        field="score"
                                        header="Relevancy"
                                        style={{ minWidth: "130px", wordWrap: "break-word" }}
                                        body={(record) => (
                                            <Box
                                                sx={{
                                                    minHeight: "60px",
                                                    maxHeight: "200px",
                                                    overflowY: "auto",
                                                    verticalAlign: "top",
                                                    pt: 0.5,
                                                    whiteSpace: "normal",
                                                    wordWrap: "break-word",
                                                    lineHeight: 1.4,
                                                    fontSize: "0.875rem",
                                                    "&::-webkit-scrollbar": { width: "6px" },
                                                    "&::-webkit-scrollbar-track": { background: "#f1f1f1", borderRadius: "3px" },
                                                    "&::-webkit-scrollbar-thumb": { background: "#c1c1c1", borderRadius: "3px" },
                                                    "&::-webkit-scrollbar-thumb:hover": { background: "#a1a1a1" },
                                                }}
                                            >
                                                {record["score"]}
                                            </Box>
                                        )}
                                    />

                                    <Column
                                        key="feedback"
                                        header="Feedback"
                                        style={{ minWidth: "110px" }}
                                        body={(record) => {
                                            const docId = getDocId(record);
                                            const current = feedbackByDoc[docId];
                                            return (
                                                <Box sx={{ display: "flex", gap: 0.5, justifyContent: "center" }}>
                                                    <Tooltip title="Relevant">
                                                        <IconButton
                                                            size="small"
                                                            color={current === "up" ? "primary" : "default"}
                                                            onClick={() => setDocFeedback(docId, "up")}
                                                        >
                                                            <ThumbUpAltOutlinedIcon fontSize="small" />
                                                        </IconButton>
                                                    </Tooltip>
                                                    <Tooltip title="Not relevant">
                                                        <IconButton
                                                            size="small"
                                                            color={current === "down" ? "error" : "default"}
                                                            onClick={() => setDocFeedback(docId, "down")}
                                                        >
                                                            <ThumbDownAltOutlinedIcon fontSize="small" />
                                                        </IconButton>
                                                    </Tooltip>
                                                </Box>
                                            );
                                        }}
                                    />
                                </DataTable>
                            </Box>
                        )}
                    </Grid>
                </Grid>
            </Box>
        </PrimeReactProvider>
    );
};
