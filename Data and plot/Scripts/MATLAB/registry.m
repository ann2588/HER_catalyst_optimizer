function registry()
% Dummy entry point. This file contains helper functions only.
end


function path_out = get_data(key)
    key = char(key); % ensure correct field name
    REG = load_registry();

    if ~isfield(REG, key)
        error("Key '%s' not found in JSON", key);
    end

    root = project_root();        % consistent project root
    data_dir = fullfile(root, "Data");

    path_out = fullfile(data_dir, REG.(key));

    if ~isfile(path_out)
        error("Key '%s' does not refer to a file: %s", key, path_out);
    end
end

function path_out = get_data_folder(key)
    key = char(key);
    REG = load_registry();

    if ~isfield(REG, key)
        error("Key '%s' not found in JSON", key);
    end

    root = project_root();
    data_dir = fullfile(root, "Data");

    path_out = fullfile(data_dir, REG.(key));

    if ~isfolder(path_out)
        error("Key '%s' does not refer to a folder: %s", key, path_out);
    end
end

function REG = load_registry()
    root = project_root();
    json_path = fullfile(root, "data_registry.json");

    txt = fileread(json_path);
    REG = jsondecode(txt);
end

function root = project_root()
    % registry.m is in: Source Code/Scripts/MATLAB
    % so go up 3 levels
    here = fileparts(mfilename('fullpath'));
    root = fullfile(here, '..', '..', '..');
end