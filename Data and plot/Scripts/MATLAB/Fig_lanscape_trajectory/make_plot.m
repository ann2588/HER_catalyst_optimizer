% ========== MATLAB Figure Template ==========

SCRIPT_DIR = fileparts(mfilename('fullpath'));
PROJECT_ROOT = fullfile(SCRIPT_DIR, '..', '..', '..');
addpath(fullfile(PROJECT_ROOT, 'Scripts', 'MATLAB'));
addpath(fullfile(PROJECT_ROOT, 'Scripts', 'MATLAB', 'utils'));

disp("Using registry from: " + which('registry'));

% Load metadata
m = metadata();

% OUTPUT DIRECTORY ROOT
OUTPUT_DIR_ROOT = fullfile(SCRIPT_DIR, '..', '..', '..', 'Figures_Main', m.stable_id);
if ~exist(OUTPUT_DIR_ROOT, 'dir')
    mkdir(OUTPUT_DIR_ROOT);
end

parentFolder = OUTPUT_DIR_ROOT;
dataFile = get_data(m.data_keys(1));

processFoldersAndPlotData(parentFolder, dataFile, 15);

function processFoldersAndPlotData(parentFolder, dataFile, zColumn, polygonVertices)

    % Load the file inside the folder 
    if isempty(dataFile)
        warning('No files found in folder %s', folderName);
    end

    % Load data from the specified file
    % Assuming one file per folder; load it
    data = readtable(dataFile, 'VariableNamingRule', 'preserve');
    data = data(:, {'Experiment', 'Cu', 'Cr', 'Se', 'V', 'Mg', 'S', 'Fe', 'Co', 'Ni', 'P', ...
    'blank', 'Volt', 'Time', 'Overpotential V at 50.0 mA cm-2'});

    if nargin < 4
        polygonVertices = 10;
    end
    
    % Define X0
    expNumbers = [59, 136, 169, 518, 590]; % for each campaign
    
    for expNumber = expNumbers
        X0 = expNumber;
        if expNumber == 59 || expNumber == 136 || expNumber == 169 || expNumber == 518 || expNumber == 590
            rNumber = 20;
        else
            rNumber = 5;
        end
        % Initialize starting and endding based on X0
        if X0 == 59
            endding = getExpIndex(data, 'exp596'); 
            starting = getExpIndex(data, 'exp609'); 
            secondending = getExpIndex(data, 'exp727');
        elseif X0 == 136
            endding = getExpIndex(data, 'exp596');  
            starting = getExpIndex(data, 'exp729'); 
            secondending = getExpIndex(data, 'exp857');
        elseif X0 == 169
            endding = getExpIndex(data, 'exp596');  
            starting = getExpIndex(data, 'exp859'); 
            secondending = getExpIndex(data, 'exp978');
        elseif X0 == 518
            endding = getExpIndex(data, 'exp596');  
            starting = getExpIndex(data, 'exp979'); 
            secondending = getExpIndex(data, 'exp1098');
        elseif X0 == 590
            endding = getExpIndex(data, 'exp596');  
            starting = getExpIndex(data, 'exp1099'); 
            secondending = getExpIndex(data, 'exp1258');
        elseif X0 == 667
            endding = getExpIndex(data, 'exp668');  
            starting = getExpIndex(data, 'exp669'); 
            secondending = getExpIndex(data, 'exp727');
        elseif X0 == 772
            endding = getExpIndex(data, 'exp788');  
            starting = getExpIndex(data, 'exp800'); 
            secondending = getExpIndex(data, 'exp857');
        elseif X0 == 891
            endding = getExpIndex(data, 'exp918');  
            starting = getExpIndex(data, 'exp919'); 
            secondending = getExpIndex(data, 'exp978');
        elseif X0 == 994
            endding = getExpIndex(data, 'exp1038');  
            starting = getExpIndex(data, 'exp1039'); 
            secondending = getExpIndex(data, 'exp1098');
        elseif X0 == 1108
            endding = getExpIndex(data, 'exp1198');  
            starting = getExpIndex(data, 'exp1199'); 
            secondending = getExpIndex(data, 'exp1258');
        else
            error('Unexpected value of X0: %d. Please set a valid X0.', X0);
        end

        
        % Define vertices of the polygon
        theta = linspace(0, 2 * pi, polygonVertices + 1); % Include endpoint for closure
        polygon_x = cos(theta(1:end-1)); % X-coordinates of vertices
        polygon_y = sin(theta(1:end-1)); % Y-coordinates of vertices
        vertices = [polygon_x', polygon_y']; % Vertices matrix
        elements = {'Cu', 'Cr', 'Se', 'V', 'Mg', 'S', 'Fe', 'Co', 'Ni', 'P'}; % Element names
        major_elements = {'S', 'P', 'Se'}; % Solid black line elements
    
        
    
    
        % Extract relevant columns
        original_weights = table2array(data(:, 2:11)); % Columns B to K
        z_values = table2array(data(:, zColumn)); % Z-values for visualization
    
        % Normalize weights for visualization
        weights = original_weights ./ 70; % Scale weights by dividing by 70
        weights = weights ./ sum(weights, 2); % Normalize rows to sum to 1
    
        % Compute Cartesian coordinates for each point
        cartesian_coords = weights * vertices; % Linear combination using weights
        x_coords = cartesian_coords(:, 1); % X-coordinates
        y_coords = cartesian_coords(:, 2); % Y-coordinates

        switch X0
            case 59
                baseName = 'campaign1_landscape';
            case 136
                baseName = 'campaign2_landscape';
            case 169
                baseName = 'campaign3_landscape';
            case 518
                baseName = 'campaign4_landscape';
            case 590
                baseName = 'campaign5_landscape';
            otherwise
                error("Unsupported X0 value: %d", X0);
        end
    
        % Define the output GIF file
        mp4FileName = fullfile(parentFolder, sprintf('%s_gif.mp4', baseName));
        video = VideoWriter(mp4FileName, 'MPEG-4');
        video.FrameRate = 5;
        video.Quality = 100;
        open(video);
    
        % Create a 2D scatter plot
        figure('Units', 'inches', 'Position', [1, 1, 6, 4.8], 'Resize', 'off', 'Color', 'w');
        hold on;
    
        % Draw radial axes
        for j = 1:polygonVertices
            if ismember(elements{j}, major_elements)
                quiver(0, 0, cos(theta(j)), sin(theta(j)), 1, 'Color', 'k', ...
                    'LineWidth', 0.75, 'MaxHeadSize', 0.2);
            else
                quiver(0, 0, cos(theta(j)), sin(theta(j)), 1, 'Color', [0.5, 0.5, 0.5], ...
                    'LineWidth', 0.75, 'LineStyle', '--', 'MaxHeadSize', 0.2);
            end
        end
    
        % Label each radial axis
        for j = 1:polygonVertices
            text(1.1 * cos(theta(j)), 1.1 * sin(theta(j)), elements{j}, ...
                'FontSize', 12, 'FontWeight', 'bold', ...
                'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle');
        end
        start = 1;
        % Scatter plot with color mapped to Z-values
        s = scatter(x_coords(start:endding), y_coords(start:endding), 50, z_values(start:endding), 'filled', 'MarkerFaceAlpha', 0.85);
        s.MarkerFaceAlpha = 1; 
        s.MarkerEdgeAlpha = 1;
        s.MarkerEdgeColor = [0.85, 0.85 ,0.85]; % Neutral gray (50% intensity)
        s.LineWidth = 0.5; % Set marker edge thickness to 0.5 pt
    
        % Highlighting X0 
        expLabel = sprintf('exp%d', expNumber);   % e.g., 'exp514'
        coorIndex = getExpIndex(data, expLabel);
        
        s_x0 = scatter(x_coords(coorIndex), y_coords(coorIndex), 200, 'Marker', '^');
        s_x0.MarkerEdgeColor = 'w';
        s_x0.MarkerFaceColor = [0,0,0];
        s_x0.LineWidth = 0.5;

        caxis([-1, 0]); % Set the color bar limits
        c = colorbar;
        configureColorBar(c, sprintf('Overpotential V vs. RHE @ 50 mA cm^{-2}')); % Font sizes in point
        % colormap(seismic()); version 1
        colormap(flipud(gray)) % version 2
        c.Position = [5.15, 0.2, 0.2, (4.8-0.3)];
    
        ax = gca;
        ax.Position = [0.05, 0.11, 0.7750, 0.8150];
    
        hold on; % Keep adding elements to the plot
    
        % Set aesthetics
        axis equal;
        axis off;
        grid off;
    
        % Pause for visualization
        s_new = scatter(x_coords(starting), y_coords(starting), 50, 'Marker', 'square');
        s_new.MarkerFaceAlpha = 1; 
        s_new.MarkerEdgeAlpha = 1;
        s_new.MarkerEdgeColor = [0.85, 0.85 ,0.85]; % Neutral gray (50% intensity)
        s_new.LineWidth = 0.5; % Set marker edge thickness to 0.5 pt
        
        n = length(x_coords(starting:secondending)); % Total number of arrows
        startColor = [1 1 1];                % 白色 RGB
        if X0 == 59
            endColor = hex2rgb("#4678C8");
        
        elseif X0 == 136
            endColor = hex2rgb("#E68C28");
        
        elseif X0 == 169
            endColor = hex2rgb("#50AA64");
        
        elseif X0 == 518
            endColor = hex2rgb("#AA5AD2");
        
        elseif X0 == 590
            endColor = hex2rgb("#2E2E2E");
        
        else
            error("Unsupported X0 value: %d", X0);
        end

        % Highlighting X0 
        expLabel = sprintf('exp%d', expNumber);   % e.g., 'exp514'
        coorIndex = getExpIndex(data, expLabel);
        
        s_x0 = scatter(x_coords(coorIndex), y_coords(coorIndex), 200, 'Marker', '^');
        s_x0.MarkerEdgeColor = endColor;
        s_x0.MarkerFaceColor = endColor;
        s_x0.LineWidth = 0.5;
       
        mapcolors = [linspace(startColor(1), endColor(1), n)', ...
                linspace(startColor(2), endColor(2), n)', ...
                linspace(startColor(3), endColor(3), n)'];
    
        %%% Animate the addition of arrows
        for i = starting:secondending-1
            % Arrow's direction
            dx = x_coords(i+1) - x_coords(i);
            dy = y_coords(i+1) - y_coords(i);
    
            % Map the current index to gray_colors
            color_idx = i - starting +1 ; % Adjust index to match gray_colors
            thisColor = mapcolors(color_idx, :);
    
            % Scatter points starting from index 609
            %scatter(x_coords(i+1), y_coords(i+1), 50, z_values(i+1), 'filled', 'square','MarkerFaceAlpha', 0.85);
            scatter(x_coords(i+1), y_coords(i+1), 50, z_values(i+1), 'filled', 'square', 'MarkerEdgeColor',thisColor, "LineWidth", 0.5);
            
            % To make the arrow reside in the center of the line
            x_start = x_coords(i);
            y_start = y_coords(i);
            x_mid = x_start + dx / 2;
            y_mid = y_start + dy / 2;
            x_arrow_start = x_mid - dx / 2;
            y_arrow_start = y_mid - dy / 2;
    
            % Plot arrow using quiver
            quiver(x_arrow_start, y_arrow_start, dx, dy, 0, ...
                    'Color', thisColor, 'MaxHeadSize', 0.15, 'LineWidth', 1.0);
        
            % Capture the frame and add to GIF
            % Capture and write frame
            frame = getframe(gcf);
            writeVideo(video, frame);
            pause(0.1);
    
        end
    
        % Save the figure
        set(gcf, 'Color', 'w'); % 'w' specifies white background

        filename = sprintf('%s.eps', baseName);
        saveFilePath = fullfile(parentFolder, filename);
        exportgraphics(gcf, saveFilePath, 'ContentType', 'vector');
        close(video);
        close(gcf);
        close all
    end
end


% =====================================================

function m = metadata()
    m.stable_id = "Fig_landscape_trajectory";
    m.script = mfilename('fullpath');
    m.data_keys = ["result_all_campaign"];
    m.figure_type = "Main";
end


function cmap = seismic()
    % SEISMIC colormap: Red-White-Blue colormap
    n = 256; % Total number of colors
    half_n = floor(n / 2);
    r = [linspace(0, 1, half_n), ones(1, half_n)];
    g = [linspace(0, 1, half_n), linspace(1, 0, half_n)];
    b = [ones(1, half_n), linspace(1, 0, half_n)];
    cmap = [r', g', b']; % Combine into RGB matrix
end

function configureColorBar(cbar, labelText, labelFontSize, tickFontSize)
    % CONFIGURECOLORBAR Customizes the color bar properties
    %
    % Inputs:
    %   cbar - Color bar handle
    %   labelText - String for the color bar label
    %   labelFontSize - Font size for the label (default: 12)
    %   tickFontSize - Font size for the tick labels (default: 8)
    %
    % Example:
    %   c = colorbar;
    %   configureColorBar(c, 'Z-Values', 14, 10);

    % Check for optional arguments and set defaults
    if nargin < 3 || isempty(labelFontSize)
        labelFontSize = 20; %       Default font size for the label
    end
    if nargin < 4 || isempty(tickFontSize)
        tickFontSize = 12; % Default font size for the tick labels
    end

    cbar.Units = 'Inches';
    cbar.Label.String = labelText;
    cbar.Label.FontSize = labelFontSize;
    cbar.Label.FontWeight = 'bold'; % Optional: Make label bold
    cbar.Label.FontName = 'Arial'; % Set the font type for the label

    % Set the tick label font size
    cbar.FontSize = tickFontSize; % Set font size for tick labels
    cbar.FontName = 'Arial'; % Ensure tick font matches label

    % Remove the color bar frame
    cbar.Box = 'off';

end

function rgb = hex2rgb(hex)
    hex = char(hex);
    if hex(1) == '#'
        hex = hex(2:end);
    end
    if numel(hex) ~= 6
        error('hex code must be 6 characters.');
    end
    r = hex2dec(hex(1:2));
    g = hex2dec(hex(3:4));
    b = hex2dec(hex(5:6));
    rgb = [r g b] / 255;
end