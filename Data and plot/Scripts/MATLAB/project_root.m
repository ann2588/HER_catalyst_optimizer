% Project root = "Source Code"
function root = project_root()
    here = fileparts(mfilename('fullpath'));
    root = fullfile(here, '..', '..');
    root = char(java.io.File(root).getCanonicalPath()); % normalize
end