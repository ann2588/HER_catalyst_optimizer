function REG = load_registry()
    root = project_root();
    json_path = fullfile(root, "data_id.json");

    txt = fileread(json_path);
    REG = jsondecode(txt);
end
