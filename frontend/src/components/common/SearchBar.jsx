import { useEffect, useState } from "react";
import { IconButton, InputAdornment, TextField, Tooltip } from "@mui/material";
import { Search as SearchIcon, ArrowForwardRounded as ArrowForwardRoundedIcon } from "@mui/icons-material";

export const SearchBar = ({ disabled, onSubmit, initQuery }) => {
    const [userQuery, setUserQuery] = useState("");

    const triggerSearch = () => {
        localStorage.setItem("user-query", userQuery);
        onSubmit();
    };

    const onEnter = (event) => {
        if (event.key === "Enter") {
            triggerSearch();
        }
    };

    useEffect(() => {
        if (initQuery) {
            setUserQuery(initQuery);
        }
    }, [initQuery]);

    return <>
        <TextField
            sx={{
                width: { xs: "100%" },
                backgroundColor: "white",
                borderRadius: 1.5,
            }}
            id="searchTerm"
            placeholder="Search ASRS..."
            variant="outlined"
            value={userQuery}
            onChange={event => { setUserQuery(event.target.value); }}
            onKeyDown={onEnter}
            disabled={disabled}
            InputProps={{
                startAdornment: (
                    <InputAdornment position="start">
                        <SearchIcon color="action" />
                    </InputAdornment>
                ),
                endAdornment: (
                    <InputAdornment position="end">
                        <Tooltip title="Search">
                            <span>
                                <IconButton
                                    edge="end"
                                    size="small"
                                    color="primary"
                                    disabled={disabled || !userQuery.trim()}
                                    onClick={triggerSearch}
                                >
                                    <ArrowForwardRoundedIcon />
                                </IconButton>
                            </span>
                        </Tooltip>
                    </InputAdornment>
                ),
            }}
        />
    </>;
};
