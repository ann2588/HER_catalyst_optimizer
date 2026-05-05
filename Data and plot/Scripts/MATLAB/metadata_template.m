% ========== MATLAB Figure Template ==========

SCRIPT_DIR = fileparts(mfilename('fullpath'));
PROJECT_ROOT = fullfile(SCRIPT_DIR, '..', '..', '..');
addpath(fullfile(PROJECT_ROOT, 'Scripts', 'MATLAB'));
addpath(fullfile(PROJECT_ROOT, 'Scripts', 'MATLAB', 'utils'));

disp("Using registry from: " + which('registry'));

% Load metadata
m = metadata();

% OUTPUT DIRECTORY ROOT
OUTPUT_DIR_ROOT = fullfile(SCRIPT_DIR, '..', '..', '..', 'Figures_SI', m.stable_id);
if ~exist(OUTPUT_DIR_ROOT, 'dir')
    mkdir(OUTPUT_DIR_ROOT);
end

% ============= Your plotting code below =============
% plot(...)

% Example of saving:
% saveas(gcf, fullfile(OUTPUT_DIR, "myplot.png"));

% =====================================================

function m = metadata()
    m.stable_id = "Fig_ovp_cdl_allcampaign";
    m.script = mfilename('fullpath');
    m.data_keys = ["All_Ovp_Cdl"];
    m.figure_type = "SI";
end