RUNNER_DIR = fileparts(mfilename('fullpath'));
ORIGINAL_DIR = pwd;
cleanupObj = onCleanup(@() cd(ORIGINAL_DIR));

plotFolders = [
    "Fig_ovp_cdl_allcampaign_Ar"
    "Fig_landscape_pretrain_Ar"
    "Fig_landscape_ecsa_Ar"
    "Fig_landscape_tafelslope_Ar"
    "Fig_landscape_exchangec_Ar"
    "Fig_lanscape_trajectory_Ar"
];

failures = strings(0);

for i = 1:numel(plotFolders)
    plotFolder = plotFolders(i);
    plotDir = fullfile(RUNNER_DIR, plotFolder);
    fprintf("Running %s...\n", plotFolder);

    try
        cd(plotDir);
        clear make_plot
        make_plot
        close all force
    catch ME
        failures(end + 1) = plotFolder + ": " + string(ME.message); %#ok<SAGROW>
        close all force
    end
end

if ~isempty(failures)
    fprintf(2, "Ar MATLAB plot failures:\n");
    for i = 1:numel(failures)
        fprintf(2, "  %s\n", failures(i));
    end
    error("One or more Ar MATLAB plot scripts failed.");
end

fprintf("All Ar MATLAB plot scripts completed.\n");
