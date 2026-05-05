function path_out = get_data(key)
    key = char(key);
    REG = load_registry();

    if ~isfield(REG, key)
        error("Key '%s' not found in JSON", key);
    end

    root = project_root();

    path_out = fullfile(root, REG.(key));

    if ~isfile(path_out)
        error("Key '%s' does not refer to a file: %s", key, path_out);
    end
end


