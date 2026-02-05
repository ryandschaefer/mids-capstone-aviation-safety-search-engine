import { DataTable } from "primereact/datatable";
import { Column } from "primereact/column";
import "primereact/resources/themes/lara-light-indigo/theme.css";
import { useEffect, useState } from "react";
import { Box, Button, Grid, Typography } from "@mui/material";
import { MetadataFilters, SearchBar } from "../common";
import { getTestData } from "../../api";
import { displayColumns } from "../../utils";
import { useNavigate } from "react-router-dom";

export const Results = () => {
    const navigate = useNavigate();

    // Binary if currently waiting on API call
    const [loading, setLoading] = useState(false);
    // Store search results
    const [searchResults, setSearchResults] = useState([]);
    // Store all records - REMOVE THIS
    const [allResults, setAllResults] = useState([]);
    // Total number of results for search
    const [totalResults, setTotalResults] = useState(-1);
    // Primereact table parameters
    const [currentPage, setCurrentPage] = useState(1);
    const [pageLength, setPageLength] = useState(10);
    // Query for the current search results
    const [userQuery, setUserQuery] = useState("");

    // Function to submit a new search query
    const onSubmit = (query) => {
        setLoading(true);
        getTestData()
            .then(x => {
                setAllResults(x);
                setTotalResults(x.length);
            })
            .finally(x => {
                setLoading(false);
                setUserQuery(query);
            });
    }

    // Function to collect a new page of results from API
    const onPage = (event) => {
        console.log(event)
        const page = event.page;
        const start = page * pageLength;
        const end = start + pageLength;
        setCurrentPage(page);
        setSearchResults(allResults.slice(start, end));
    }

    // Load initial results
    useEffect(() => {
        onSubmit();
    }, []);

    // Set to first page when total results changes
    useEffect(() => {
        setCurrentPage(1);
        onPage({ page: 0 });
    }, [totalResults]);

    return <>
        <Box
            sx={{
                display: 'flex', 
                flexDirection: "column",
                textAlign: "center",
            }}
        >
            <Grid 
                container 
                rowSpacing={3 }
                sx={{ 
                    // backgroundColor: '#f8f9fa',
                    mt: "5dvh",
                }}
            >
                {/* Home button */}
                <Grid size = {1}>
                    <Box
                        sx = {{
                            textAlign: "center",
                        }}
                    >
                        <Button
                            onClick = {() => navigate("/")}
                        >
                            Aviation Safety Search
                        </Button>
                    </Box>
                </Grid>

                {/* Search bar */}
                <Grid size = {8}>
                    <Box
                        sx = {{
                            width: "80%",
                            alignItems: "center",
                            ml: "10%"
                        }}
                    >
                        <SearchBar
                            disabled={loading}
                            onSubmit={onSubmit}
                        />
                    </Box>
                </Grid>

                {/* Metadata filters button */}
                <Grid size = {3}>
                    <Box
                        sx={{
                            float: "left"
                        }}
                    >
                        <MetadataFilters
                            disabled={loading}
                        />
                    </Box>
                </Grid>

                {/* Results table */}
                <Grid size={12}>
                    {/* Loading spinner while waiting on search */}
                    {loading && (
                        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: { xs: 3, sm: "50px" }, width: '100%' }}>
                            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
                                <div className="spinner-border" style={{ width: "5rem", height: "5rem" }} role="status">
                                    <span className="sr-only"></span>
                                </div>
                            </div>
                        </Box>
                    )}

                    {/* Results table once search is complete */}
                    {!loading && (
                        <Box>
                            <Typography
                                variant="p"
                            >
                                There were { totalResults } results for "{ userQuery }"
                            </Typography>
                            <DataTable
                                value={searchResults}
                                scrollable
                                showBoxlines
                                stripedRows
                                style={{ width: '100%', maxWidth: '100%' }}
                                lazy={true}
                                paginator={true}
                                rows={pageLength}
                                totalRecords={totalResults}
                                onPage={onPage}
                                first={currentPage * pageLength}
                                emptyMessage="No Records Found"
                                paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
                                currentPageReportTemplate="Showing {first} to {last} of {totalRecords} entries"
                            >
                                {/* Display selected columns */}
                                {displayColumns.map((col, i) => {
                                    const id = col["id"]
                                    const colName = col["name"]

                                    return <Column
                                        key = {i}
                                        field = {id}
                                        header = {colName}
                                        style = {{
                                            minWidth: "130px",
                                            wordWrap: "break-word"
                                        }}
                                        body = {(record) => {
                                            // Format table cells
                                            return <Box
                                                sx = {{
                                                    minHeight: '60px',
                                                    maxHeight: '200px',
                                                    overflowY: 'auto',
                                                    verticalAlign: 'top',
                                                    pt: 0.5,
                                                    whiteSpace: 'normal',
                                                    wordWrap: 'break-word',
                                                    lineHeight: 1.4,
                                                    fontSize: '0.875rem',
                                                    '&::-webkit-scrollbar': { width: '6px' },
                                                    '&::-webkit-scrollbar-track': { 
                                                        background: '#f1f1f1', 
                                                        borderRadius: '3px' 
                                                    },
                                                    '&::-webkit-scrollbar-thumb': { 
                                                        background: '#c1c1c1', 
                                                        borderRadius: '3px' 
                                                    },
                                                    '&::-webkit-scrollbar-thumb:hover': { 
                                                        background: '#a1a1a1' 
                                                    }
                                                }}
                                            >
                                                { record[id] }
                                            </Box>
                                        }}
                                    />
                                })}
                            </DataTable>
                        </Box>
                    )}
                </Grid>
            </Grid>
        </Box>
    </>
}